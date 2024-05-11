#!/usr/bin/python3
"""
This script imports all the "Other" visit types from the old JKMR app to the new SITE VISIT RECORDS app.
"""
import argparse
import builtins
import copy
import json
import logging
import os
import time
import typing as t

from dotenv import load_dotenv
from fulcrum import Fulcrum
from fulcrum_types.types import (App, AppElement, AppElementTypes, FormValue,
                                 Record, RepeatableValue)

load_dotenv()

parser = argparse.ArgumentParser(
    description="Import all the 'Other' visit types from the old JKMR app to the new SITE VISIT RECORDS app."
)
parser.add_argument(
    "--debug", help="Whether we should run in debug mode or not", action="store_true"
)
parser.add_argument(
    "--no-confirmation", help="Whether we should run without confirmation", action="store_true"
)
parser.add_argument(
    "--skip-missing", help="Whether we should skip records that don't have a matching record in the new app", action="store_true"
)

# Parse the arguments
args = parser.parse_args()

DEBUG = args.debug
NO_CONFIRMATION = args.no_confirmation
SKIP_MISSING = args.skip_missing

# Get the Fulcrum API key from the environment variables
FULCRUM_API_KEY = os.getenv("FULCRUM_API_KEY")
# Create the Fulcrum API object
FULCRUM = Fulcrum(FULCRUM_API_KEY)

# The name of the old JKMR app and the new SITE VISIT RECORDS app
JKMR_APP_NAME = "Japanese Knotweed Management Record (LEGACY)"
# SITE_VISIT_RECORDS_APP_NAME = "SITE VISIT RECORDS"
SITE_VISIT_RECORDS_APP_NAME = "SITE VISIT RECORDS - COPY (DO NOT USE)"

# The list of files created
FILES_CREATED = []

# The list of debug files created, to be deleted at the end of the script
DEBUG_FILES_CREATED = []

# The app structures
JKMR_APP = None # type: t.Union[App, None]
SITE_VISIT_RECORDS_APP = None # type: t.Union[App, None]

# Key names that are important to know
KEY_NAMES = {
    "JKMR": {
        # Match records on values of these keys
        # These are the same by coincidence (it does not need to change)
        "pba_reference": "c4ee",
        "site_address": "1b4b",
        # End of matching keys
        "other_visit_repeatable": "86df",
        "treatment_date": "4bed",
        "technicians_names": "16cd",
        "other_site_visit_date": "4bed",
        "other_site_visit_time": "d7ff",
    },
    "SITE_VISIT_RECORDS": {
        # Match records on values of these keys
        "job_id": "c4ee",
        "site_address": "48ca",
        # End of matching keys
        "site_visit_entries": "3bdb",
        "site_visit_date": "8eaf",
        "site_visit_time": "2a76",
        "visit_category": "4010",
        "record_type_japanese_knotweed": "b0b0",
        "visit_type_japanese_knotweed_other": "113b",
    },
}

# Logging format of: [LEVEL]::[FUNCTION]::[HH:MM:SS] - [MESSAGE]
# Where the level is colored based on the level and the rest except from the message is grey
start = "\033["
end = "\033[0m"
colors = {
    "GREEN": "32m",
    "ORANGE": "33m",
    "RED": "31m",
    "GREY": "90m",
}
for color in colors:
    # Add the start to the color
    colors[color] = start + colors[color]

logging.addLevelName(logging.DEBUG, f"{colors['GREEN']}DEBUG{colors['GREY']}")  # Green
logging.addLevelName(logging.INFO, f"{colors['GREEN']}INFO{colors['GREY']}")  # Green
logging.addLevelName(
    logging.WARNING, f"{colors['ORANGE']}WARNING{colors['GREY']}"
)  # Orange
logging.addLevelName(logging.ERROR, f"{colors['RED']}ERROR{colors['GREY']}")  # Red
logging.addLevelName(
    logging.CRITICAL, f"{colors['RED']}CRITICAL{colors['GREY']}"
)  # Red

# Define the format of the logging
logging.basicConfig(
    format=f"%(levelname)s::%(funcName)s::%(asctime)s - {end}%(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG if args.debug else logging.INFO)

# Add a file handler to the logger
file_handler = logging.FileHandler(
    os.path.dirname(os.path.realpath(__file__)) + "/import_other_visits.log",
    mode="w+",
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(
    logging.Formatter(
        f"%(levelname)s::%(funcName)s::%(asctime)s - %(message)s", datefmt="%H:%M:%S"
    )
)
logger.addHandler(file_handler)


def list_apps():
    """
    List all the apps in the Fulcrum account
    """
    apps = FULCRUM.forms.search()["forms"]
    logger.debug(f"Found {len(apps)} apps")
    return apps


def get_app(name: str) -> App:
    """
    Get an app by name
    """
    logger.info(f"Getting app: {name}")
    apps = list_apps()
    for app in apps:
        if app["name"] == name:
            return app # type: App


def open(filename: str, mode, debug_file=False):
    """
    Override builtin "open" function to open file but add filename to the global list of files
    This is so we can delete them later
    """
    global FILES_CREATED
    FILES_CREATED.append(filename)

    if debug_file:
        global DEBUG_FILES_CREATED
        DEBUG_FILES_CREATED.append(filename)

    return builtins.open(os.path.join(os.path.dirname(__file__), filename), mode)


def get_app_records(app: dict) -> t.List[Record]:
    """
    Get the records of a specific app
    """
    records = FULCRUM.records.search({"form_id": app["id"]})["records"]
    return records


def deep_convert_none_fields(hash: dict) -> dict:
    """
    Deep convert all the None values in a dictionary to an empty string
    """
    for key, value in hash.items():
        if value is None:
            hash[key] = ""
        elif isinstance(value, dict):
            hash[key] = deep_convert_none_fields(value)

    return hash


def deep_convert_fields(hash: dict) -> dict:
    """
    Deep convert all values in a field to a format that can be compared
    """
    return deep_strip_fields(deep_convert_none_fields(hash))


def deep_strip_fields(hash: dict) -> dict:
    """
    Deep strip all the string values in a dictionary
    """
    for key, value in hash.items():
        if isinstance(value, str):
            hash[key] = value.strip()
        elif isinstance(value, dict):
            hash[key] = deep_strip_fields(value)

    return hash


SITE_VISIT_HASH = {}  # type: t.Dict[str, Record]


def find_matching_site_visit_record(
    jkmr_record: Record, site_visit_records: t.List[Record]
) -> t.Optional[Record]:
    """
    Find a matching site visit record for a JKMR record
    """
    global SITE_VISIT_HASH
    if not SITE_VISIT_HASH:
        SITE_VISIT_HASH = {
            record["form_values"]
            .get(KEY_NAMES["SITE_VISIT_RECORDS"]["job_id"], "")
            .strip(): record
            for record in site_visit_records
        }

    jkmr_job_id = (
        jkmr_record["form_values"].get(KEY_NAMES["JKMR"]["pba_reference"], "")
    ).strip()

    focus_site_record = SITE_VISIT_HASH.get(jkmr_job_id, None)

    if not focus_site_record:
        logger.warning(
            f"Could not find a matching site visit record for JKMR record: {jkmr_record['id']} - {jkmr_job_id}"
        )
        return None

    logger.info(
        f"Found matching site visit record for JKMR record: {jkmr_record['id']} - {jkmr_job_id}"
    )

    comparissons = [
        [
            deep_convert_fields(
                jkmr_record["form_values"].get(KEY_NAMES["JKMR"]["site_address"], {})
            ),
            deep_convert_fields(
                focus_site_record["form_values"].get(
                    KEY_NAMES["SITE_VISIT_RECORDS"]["site_address"], {}
                )
            ),
        ],
    ]

    matches = compare_comparissons(comparissons, False)

    if matches:
        return focus_site_record


def get_jkmr_other_site_visits(jkmr_record: Record) -> t.List[RepeatableValue]:
    """
    Get all the "Other" site visit records from a JKMR record
    """
    other_site_visits = jkmr_record["form_values"].get(
        KEY_NAMES["JKMR"]["other_visit_repeatable"], None
    )

    # Not all records have an "Other" site visit repeatable
    if other_site_visits == None:
        logger.warning(
            f"Could not find 'Other' site visits for JKMR record: {jkmr_record['id']}"
        )
        return []

    logger.debug(f"Other site visits: {other_site_visits}")
    logger.info(
        f"Found {len(other_site_visits)} 'Other' site visits for JKMR record: {jkmr_record['id']}"
    )

    return other_site_visits


def get_site_visit_entries(site_visit_record: Record) -> t.List[FormValue]:
    """
    Get the site visit entries from a site visit record
    """
    site_visit_entries = site_visit_record["form_values"].get(
        KEY_NAMES["SITE_VISIT_RECORDS"]["site_visit_entries"], None
    )

    if site_visit_entries == None:
        logger.warning(
            f"Could not find 'Other' site visits for site visit record: {site_visit_record['id']}"
        )
        return []

    logger.debug(f"Site visit entries: {site_visit_entries}")

    return site_visit_entries


def compare_comparissons(
    comparissons: t.List[t.List[t.Any]], falsy_matches=True
) -> bool:
    """
    Compare a list of comparissons and return whether they are the same or not
    """

    matches = True

    for values in comparissons:
        # Check whether we should match None values or just return False
        if not falsy_matches:
            # If any of the values are None, then don't match
            if not values[0] or not values[1]:
                logger.debug(
                    f"One of the values is falsy, not matching: {values[0]}, {values[1]}"
                )
                matches = False
                break

        # If the values are not the same, then it does not match
        if not do_form_values_match(values[0], values[1]):
            logger.debug(f"Comparisson: {values[0]} != {values[1]}")
            matches = False
            break

        logger.debug(f"Comparisson: {values[0]} == {values[1]}")

    return matches


def do_form_values_match(value1: t.Any, value2: t.Any) -> bool:
    """
    Check if two form values match
    """
    converted_value1 = (
        deep_convert_fields(value1) if isinstance(value1, dict) else value1
    )
    converted_value2 = (
        deep_convert_fields(value2) if isinstance(value2, dict) else value2
    )

    return converted_value1 == converted_value2


def get_matching_site_visits(
    source_visit: RepeatableValue, visits: t.List[RepeatableValue]
) -> t.List[RepeatableValue]:
    """
    Get the matching site visit from the list of site visits
    """

    matching_visits = []

    for visit in visits:
        """
        ? This should be passed into the function rather than defined here
        because otherwise this function isn't pure
        """
        comparissons = [
            [
                source_visit["form_values"].get(
                    KEY_NAMES["JKMR"]["treatment_date"], None
                ),
                visit["form_values"].get(
                    KEY_NAMES["SITE_VISIT_RECORDS"]["site_visit_date"], None
                ),
            ],
            [
                # Create the "Other" object that we want to match on
                # Simulate what the "Other" object would look like in the site visit record
                # We are essentially matching on site visit type here since we already know that the
                # source_visit will be of type "Other"
                {
                    "other_values": [],
                    "choice_values": ["Other Treatments Inc. Excavation"],
                },
                visit["form_values"].get(
                    KEY_NAMES["SITE_VISIT_RECORDS"]["record_type_japanese_knotweed"],
                    None,
                ),
            ],
        ]

        # Check if all the comparissons match
        matches = compare_comparissons(comparissons, False)

        if matches:
            matching_visits.append(visit)

    return matching_visits


def find_key_code(elements: t.List[AppElement], data_name: str) -> str | None:
    """
    Recursively search an app's elements to find the key
    code of a field in an app
    """
    section_types = [
        "Section",
        "Repeatable",
    ] # type: AppElementTypes

    for element in elements:
        if element["data_name"] == data_name:
            return element["key"]

        if element["type"] in section_types:
            key_code = find_key_code(element["elements"], data_name)
            if key_code:
                return key_code

    return None

def update_site_visit_record_with_entry(
        parent_site_visit_record: Record, new_entry: RepeatableValue
):
    """
    Update the site visit record with a new entry
    """

    global SITE_VISIT_RECORDS_APP

    if not SITE_VISIT_RECORDS_APP:
        logger.error("SITE VISIT RECORDS app is not defined")
        exit(1)

    updated_parent_site_visit_record = copy.deepcopy(parent_site_visit_record)

    # Find the insertion point within the parent site visit record
    site_visit_entries = get_site_visit_entries(parent_site_visit_record)

    updated_site_visit_entries = copy.deepcopy(site_visit_entries)

    # Add the new entry to the site visit record
    updated_site_visit_entries.append(new_entry)

    # Sort the site visit entries by date and time on using SITE VISIT RECORDS keys
    updated_site_visit_entries.sort(
        key=lambda x: (
            x["form_values"].get(KEY_NAMES["SITE_VISIT_RECORDS"]["site_visit_date"], ""),
            x["form_values"].get(KEY_NAMES["SITE_VISIT_RECORDS"]["site_visit_time"], ""),
        )
    )

    # Update the parent site visit record with the new entries
    updated_parent_site_visit_record["form_values"][KEY_NAMES["SITE_VISIT_RECORDS"]["site_visit_entries"]] = updated_site_visit_entries

    # Log the changes to a file with the ID as the filename in the "changes" directory
    if not os.path.exists(os.path.join(os.path.dirname(__file__), "changes")):
        os.mkdir(os.path.join(os.path.dirname(__file__), "changes"))

    with open(f"changes/{parent_site_visit_record['id']}_before.txt", "w") as f:
        json.dump(parent_site_visit_record, f, indent=4)

    with open(f"changes/{parent_site_visit_record['id']}_after.txt", "w") as f:
        json.dump(updated_parent_site_visit_record, f, indent=4)

    if not NO_CONFIRMATION:
        user_input = input(
            f"Update site visit record {parent_site_visit_record['id']} with new entry? (y/n):"
        )

        if user_input.lower() != "y":
            logger.error("User chose not to update the site visit record, exiting...")
            exit(1)

    # Update the site visit record
    update_fulcrum_record(parent_site_visit_record["id"], updated_parent_site_visit_record)


def rate_limited(max_per_second):
    """
    Decorator to limit the rate of function calls.
    """
    minimum_interval = 1.0 / float(max_per_second)

    def decorate(func):
        last_time_called = [0.0]

        def rate_limited_function(*args, **kargs):
            elapsed = time.perf_counter() - last_time_called[0]
            left_to_wait = minimum_interval - elapsed
            if left_to_wait > 0:
                time.sleep(left_to_wait)
            ret = func(*args, **kargs)
            last_time_called[0] = time.perf_counter()
            return ret

        return rate_limited_function

    return decorate


# Rate limited for 4000 calls per hour (actual limit is 5000/h but we want to be safe)
@rate_limited(4000 / 3600)
def update_fulcrum_record(record_id: str, record: Record):
    """
    Update a record in Fulcrum
    """
    # Update the site visit record
    FULCRUM.records.update(
        record_id, record
    )

def process_new_site_visit_entry(
    parent_site_visit_record: Record, jkmr_other_visit: RepeatableValue
):
    """
    Process a new site visit entry
    Safely add the new site visit entry to the parent site visit record
    This function is called when we have found a JKMR other site visit entrythat does not exist in
    the SITE VISIT RECORDS app
    """

    # Field keys need to be obtained and translated from the JKMR app to the SITE VISIT RECORDS app
    # The structure may need changing also:
    # 1. Look in the JKMR app to see how the entry is structured
    # 2. Get the JKMR app structure and field keys
    # 3. Get the SITE VISIT RECORDS app structure and field keys
    # 4. Translate the JKMR app field keys to the new SITE VISIT RECORDS app field keys
    # 5. For any SITE VISIT RECORD app field keys that aren't populated, see if this field
    #    can be populated from the parent JKMR record or determined using some other method.
    # 6. With a new entry created, we can update the existing SITE VISIT RECORD app record
    #    with the new entries.

    global JKMR_APP
    global SITE_VISIT_RECORDS_APP

    if not JKMR_APP:
        logger.error("JKMR app is not defined")
        exit(1)

    if not SITE_VISIT_RECORDS_APP:
        logger.error("SITE VISIT RECORDS app is not defined")
        exit(1)

    # Key mappings from JKMR to SITE VISIT RECORDS
    # We use these data names to find the key codes in the app
    data_name_mapping = {
        "treatment_date": "visit_date",
        "treatment_start_time": "start_time",
        "technicians_names": "personnel_details_qualifications",
        "treatment_types": "visit_type_japanese_knotweed_other",
        "does_site_for_treatment_meet_generic_rams_criteria": "does_site_meet_raams_criteria",
        "can_the_additional_treatment_proceed": "can_the_planned_works_proceed",
        "site_specific_risk_assessment_additional_treatment": "site_specific_risk_assessment",
        "additional_treatment_not_proceeding_reasons": "site_specific_risk_assessment",
        "supplementary_treatment_carried_out": "supplementary_treatment_carried_out",
        "reasons_for_treatment_not_proceeding_or_interrupted": "reasons_for_treatment_not_taking_place_or_treatment_other",
        "supplementary_treatment_notes": "notes",
        "audio_notes": "",
        "supplementary_treatment_photos": "photos",
        "supplementary_treatment_video": "video",
    }

    # A key code is a 4 digit code that is used to identify a field in the app
    # The first index in the list is the JKMR key code and the second index is the SITE VISIT RECORDS key code
    key_code_mappings = {} # type: t.Dict[str, t.List[str]]

    # Populate the key code mappings
    for jkmr_data_name, site_visit_data_name in data_name_mapping.items():
        if not jkmr_data_name or not site_visit_data_name:
            logger.warning(f"Skipping key code mapping for \"{jkmr_data_name}\" -> \"{site_visit_data_name}\", because one of the values is empty")
            continue

        jkmr_key_code = find_key_code(JKMR_APP["elements"], jkmr_data_name)
        site_visit_key_code = find_key_code(SITE_VISIT_RECORDS_APP["elements"], site_visit_data_name)

        if not jkmr_key_code:
            logger.error(f"Could not find key code for JKMR data name: {jkmr_data_name}")
            exit(1)

        if not site_visit_key_code:
            logger.error(f"Could not find key code for SITE VISIT RECORDS data name: {site_visit_data_name}")
            exit(1)

        logger.debug(f"Found key code for JKMR data name: \"{jkmr_data_name}\" -> \"{jkmr_key_code}\"")
        logger.debug(f"Found key code for SITE VISIT RECORDS data name: \"{site_visit_data_name}\" -> \"{site_visit_key_code}\"")

        logger.debug(f"Adding key code mapping for \"{jkmr_data_name}\" -> \"{site_visit_data_name}\"")
        key_code_mappings[jkmr_data_name] = [jkmr_key_code, site_visit_key_code]

    # Now we have the key code mappings, we can start creating the new site visit entry
    updated_jkmr_other_visit = copy.deepcopy(jkmr_other_visit)

    # Translate the keys from JKMR to SITE VISIT RECORDS (if required)
    for data_name, keys in key_code_mappings.items():
        old_key = keys[0]
        new_key = keys[1]

        if old_key not in updated_jkmr_other_visit["form_values"]:
            logger.warning(f"Skipping the translation of key: \"{old_key}\" since it was not found in JKMR other visit entry: {jkmr_other_visit}")
            continue

        # Update the key
        logger.debug(f"Translating key: \"{old_key}\" -> \"{new_key}\" for data name: \"{data_name}\"")
        updated_jkmr_other_visit["form_values"][new_key] = updated_jkmr_other_visit["form_values"].pop(old_key)

    # Make some other required changes for "Other" site visit entries
    visit_category_value = "Japanese Knotweed Management Record"
    logger.debug(f"Updating the visit_category to: {visit_category_value}")
    updated_jkmr_other_visit["form_values"][KEY_NAMES["SITE_VISIT_RECORDS"]["visit_category"]] = visit_category_value
    record_type_value = "Other Treatments Inc. Excavation"
    logger.debug(f"Updating the record_type_japanese_knotweed to: {record_type_value}")
    updated_jkmr_other_visit["form_values"][KEY_NAMES["SITE_VISIT_RECORDS"]["record_type_japanese_knotweed"]] = record_type_value

    # Log the changes to a file with the ID as the filename in the "changes" directory
    if not os.path.exists(os.path.join(os.path.dirname(__file__), "changes")):
        os.mkdir(os.path.join(os.path.dirname(__file__), "changes"))

    with open(f"changes/{parent_site_visit_record['id']}.txt", "w") as f:
        json.dump(jkmr_other_visit, f, indent=4)

    # Add the new entry to the site visit record
    update_site_visit_record_with_entry(parent_site_visit_record, updated_jkmr_other_visit)


def process_existing_site_visit_entry(
    jkmr_other_visit: RepeatableValue,
    parent_site_visit_record: Record,
):
    """
    Process an existing site visit entry
    """
    logger.info(f"Site visit already exists, manually added? {jkmr_other_visit}")

    # Just log it to a file for manual inspection
    with open("existing_site_visit_entries.txt", "a") as f:
        f.write(f"{parent_site_visit_record['id']} -> {jkmr_other_visit["form_values"].get(KEY_NAMES["JKMR"]["treatment_date"], jkmr_other_visit["id"])}\n")

    # We don't do any processing here since the site visit entry already exists
    # Manual inspection is required for ensuring that the data has been transferred correctly


def process_site_visit_record_update(
    site_visit_record: Record, jkmr_other_visits: t.List[RepeatableValue]
):
    """
    Processes the update of a site visit record
    """
    for jkmr_other_visit in jkmr_other_visits:
        # Get the site visit entries
        site_visit_other_vists = get_site_visit_entries(site_visit_record)

        # Find a matching site visit if there is one
        matching_site_visits = get_matching_site_visits(
            jkmr_other_visit, site_visit_other_vists
        )

        processing_type = (
            False
        )  # type: t.Literal['new_entry', 'existing_entry', 'error_out']

        # If we have no matching site visit entry
        if len(matching_site_visits) == 0:
            logger.info(
                f"Could not find a matching site visit for JKMR other visit entry: {jkmr_other_visit}"
            )
            processing_type = "new_entry"

        # If we have more than 1 matching site visit entry
        if len(matching_site_visits) > 1:
            logger.error(
                f"Found more than one matching site visit for JKMR record: {jkmr_other_visit}"
            )

            # Ask the user to specify which one to use
            user_input = input(
                f"Found more than one matching site visit for JKMR record: {jkmr_other_visit}.\n"
                + "Please specify the ID of which one to use:"
                + f"{'\n'.join([visit['id'] for visit in matching_site_visits])}\n"
            )

            matching_site_visits = [
                visit for visit in matching_site_visits if visit["id"] == user_input
            ]

            if len(matching_site_visits) == 0:
                logger.error(
                    f"Could not find the specified site visit for JKMR record: {jkmr_other_visit}"
                )
                processing_type = "error_out"

        # If we have a matching site visit entry
        if len(matching_site_visits) == 1:
            logger.info(
                f"Found matching site visit for JKMR other visit entry: {jkmr_other_visit}"
            )
            processing_type = "existing_entry"

        # Process depending on process type
        if processing_type == "new_entry":
            process_new_site_visit_entry(site_visit_record, jkmr_other_visit)
        elif processing_type == "existing_entry":
            process_existing_site_visit_entry(
                jkmr_other_visit, site_visit_record
            )
        elif processing_type == "error_out":
            logger.error("Exiting...")
            exit(1)


def prompt_user_for_record_mapping(record_id: str) -> t.Union[t.Literal["skip"], str]:
    """
    Prompt the user to skip a record or map it to another record ID
    """
    if os.path.exists(os.path.join(os.path.dirname(__file__), "record_mappings.txt")):
        with open("record_mappings.txt", "r") as f:
            record_mappings = f.readlines()

            for record_mapping in record_mappings:
                mappings = record_mapping.strip().split(" -> ")
                if mappings[0].strip() == record_id:
                    logger.info(
                        f"Found record mapping for record ID {record_id}: {record_mapping}"
                    )
                    return mappings[1].strip()

    if os.path.exists(os.path.join(os.path.dirname(__file__), "skip_preferences.txt")):
        with open("skip_preferences.txt", "r") as f:
            skip_preferences = f.readlines()

        if record_id in skip_preferences:
            logger.info(
                f"Skipping record {record_id} as per user preference in skip_preferences.txt"
            )
            return "skip"

    if SKIP_MISSING:
        logger.info("Skipping record since --skip-missing was defined...")
        return "skip"

    user_input = input(
        f"Could not find matching site visit record for JKMR record: {record_id}.\n"
        + "Do you want to skip this record or enter a record ID that we should match with? (y/n/record_id):\n"
    ).strip()

    if user_input.lower() == "y":
        logger.info("Skipping record...")
        logger.info("Saving skip preference to file...")
        # Save the skip preference to a file so we can skip this record in future runs
        with open("skip_preferences.txt", "a") as f:
            f.write(f"{record_id}\n")

        return "skip"
    elif user_input.lower() == "n":
        logger.error("User chose not to skip the record, exiting...")
        exit(1)
    else:
        logger.info(f"Record ID entered: {user_input}")

        # Save record mapping to a file
        with open("record_mappings.txt", "a") as f:
            f.write(f"{record_id} -> {user_input}\n")

        return user_input


def main():
    """
    Main function of the script.
    """

    # Get the apps
    global JKMR_APP
    JKMR_APP = get_app(JKMR_APP_NAME)

    global SITE_VISIT_RECORDS_APP
    SITE_VISIT_RECORDS_APP = get_app(SITE_VISIT_RECORDS_APP_NAME)

    if not JKMR_APP:
        logger.error(f"Could not find the '{JKMR_APP_NAME}' app")
        exit(1)

    if not SITE_VISIT_RECORDS_APP:
        logger.error(f"Could not find the '{SITE_VISIT_RECORDS_APP_NAME}' app")
        exit(1)

    # Get the records
    jkmr_records = get_app_records(JKMR_APP)
    site_visit_records = get_app_records(SITE_VISIT_RECORDS_APP)

    for jkmr_record in jkmr_records:
        # Preliminary check to see if the record has any "Other" site visits
        # Get the "other" site visit entries
        jkmr_other_site_visits = get_jkmr_other_site_visits(jkmr_record)

        if jkmr_record['id'] == "d710aa13-6e9b-4bf6-9ac8-0b909629eb96":
            pass

        # If there are no "other" site visits then we can skip this JKMR record
        if len(jkmr_other_site_visits) == 0:
            logger.info("JKMR record has no 'Other' site visits, skipping...")
            continue

        # Attempt to find a matching record in the new app
        matching_site_visit_record = find_matching_site_visit_record(
            jkmr_record, site_visit_records
        )

        # We should always have a match unless this record hasn't been imported
        # All records should've been transferred over even if there are no "other" site visit entries
        if not matching_site_visit_record:
            logger.warning(
                f"Could not find matching site visit record for JKMR record: {jkmr_record['id']}"
            )

            # Prompt the user for permission to skip this record
            record_mapping = prompt_user_for_record_mapping(jkmr_record["id"])
            if record_mapping == "skip":
                continue

            # Get the matching site visit record
            for site_visit_record in site_visit_records:
                if site_visit_record["id"] == record_mapping:
                    matching_site_visit_record = site_visit_record
                    break

            if not matching_site_visit_record:
                logger.error(
                    f"Could not find matching site visit record for user defined (file/input) value {record_mapping} for JKMR record: {jkmr_record['id']}"
                )
                exit(1)

        # Process the site visit record update
        logger.info(
            f"Found matching site visit record for JKMR record: {jkmr_record['id']}"
        )
        logger.debug("Processing the site visit record update")
        process_site_visit_record_update(
            matching_site_visit_record, jkmr_other_site_visits
        )


if __name__ == "__main__":
    main()
