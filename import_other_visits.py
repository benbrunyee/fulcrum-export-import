#!/usr/bin/python3
"""
This script imports all the "Other" visit types from the old JKMR app to the new SITE VISIT RECORDS app.
"""
import argparse
import builtins
import logging
import os
import typing as t

from dotenv import load_dotenv
from fulcrum import Fulcrum

from fulcrum_types.types import FormValue, Record, RepeatableValue

load_dotenv()

parser = argparse.ArgumentParser(
    description="Import all the 'Other' visit types from the old JKMR app to the new SITE VISIT RECORDS app."
)
parser.add_argument(
    "--debug", help="Whether we should run in debug mode or not", action="store_true"
)

# Parse the arguments
args = parser.parse_args()

DEBUG = args.debug

# Get the Fulcrum API key from the environment variables
FULCRUM_API_KEY = os.getenv("FULCRUM_API_KEY")
# Create the Fulcrum API object
FULCRUM = Fulcrum(FULCRUM_API_KEY)

# The name of the old JKMR app and the new SITE VISIT RECORDS app
JKMR_APP_NAME = "Japanese Knotweed Management Record (LEGACY)"
SITE_VISIT_RECORDS_APP_NAME = "SITE VISIT RECORDS"

# The list of files created
FILES_CREATED = []

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


def list_apps():
    """
    List all the apps in the Fulcrum account
    """
    apps = FULCRUM.forms.search()["forms"]
    logger.debug(f"Found {len(apps)} apps")
    return apps


def get_app(name: str):
    """
    Get an app by name
    """
    apps = list_apps()
    for app in apps:
        if app["name"] == name:
            return app


def open(filename, mode):
    """
    Override builtin "open" function to open file but add filename to the global list of files
    This is so we can delete them later
    """
    global FILES_CREATED
    FILES_CREATED.append(filename)
    return builtins.open(filename, mode)


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


def find_matching_site_visit_record(
    jkmr_record: Record, site_visit_records: t.List[Record]
) -> t.Optional[Record]:
    """
    Find a matching site visit record for a JKMR record
    """
    jkmr_job_id = jkmr_record["form_values"].get(
        KEY_NAMES["JKMR"]["pba_reference"], None
    )

    for site_visit_record in site_visit_records:
        # The values to compare
        # The first value is from the JKMR record and the second is from the site visit record
        # This is the required structure for the comparissons since we use these indexes later on
        site_visit_job_id = site_visit_record["form_values"].get(
            KEY_NAMES["SITE_VISIT_RECORDS"]["job_id"], None
        )
        comparissons = [
            [
                jkmr_job_id,
                site_visit_job_id,
            ],
            [
                deep_convert_none_fields(
                    jkmr_record["form_values"].get(
                        KEY_NAMES["JKMR"]["site_address"], {}
                    )
                ),
                deep_convert_none_fields(
                    site_visit_record["form_values"].get(
                        KEY_NAMES["SITE_VISIT_RECORDS"]["site_address"], {}
                    )
                ),
            ],
        ]

        matches = compare_comparissons(comparissons)

        if matches:
            return site_visit_record

    logger.warn(
        f"Could not find a matching site visit record for JKMR record: {jkmr_record['id']} - {jkmr_job_id}"
    )
    return None


def get_jkmr_other_site_visits(jkmr_record: Record) -> t.List[FormValue]:
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
    comparissons: t.List[t.List[t.Any]], none_matches=True
) -> bool:
    """
    Compare a list of comparissons and return whether they are the same or not
    """

    matches = True

    for values in comparissons:
        # Check whether we should match None values or just return False
        if not none_matches:
            # If any of the values are None, then don't match
            if values[0] == None or values[1] == None:
                logger.debug(
                    f"One of the values is None, not matching: {values[0]}, {values[1]}"
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
        deep_convert_none_fields(value1) if isinstance(value1, dict) else value1
    )
    converted_value2 = (
        deep_convert_none_fields(value2) if isinstance(value2, dict) else value2
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
                    "choice_values": ["Other"],
                },
                visit["form_values"].get(
                    KEY_NAMES["SITE_VISIT_RECORDS"]["visit_category"], None
                ),
            ],
        ]

        # Check if all the comparissons match
        matches = compare_comparissons(comparissons, False)

        if matches:
            matching_visits.append(visit)

    return matching_visits


def process_site_visit_record_update(
    site_visit_record: Record, jkmr_other_visits: t.List[FormValue]
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

        potentially_applicable_for_further_processing = False

        # Check if we found a matching site visit
        if len(matching_site_visits) == 0:
            logger.info(
                f"Could not find a matching site visit for JKMR other visit entry: {jkmr_other_visit}"
            )
            potentially_applicable_for_further_processing = True

        if len(matching_site_visits) > 1:
            logger.error(
                f"Found more than one matching site visit for JKMR record: {jkmr_other_visit}"
            )
            exit(1)

        if len(matching_site_visits) == 1:
            matching_site_visit = matching_site_visits[0]
            logger.info(
                f"Found matching site visit for JKMR other visit entry: {jkmr_other_visit}"
            )
            potentially_applicable_for_further_processing = True

        if potentially_applicable_for_further_processing:
            logger.debug(
                f"Potentially applicable for further processing: {jkmr_other_visit}"
            )


def main():
    """
    Main function of the script.
    """
    jkmr_app = get_app(JKMR_APP_NAME)
    site_visit_records_app = get_app(SITE_VISIT_RECORDS_APP_NAME)

    if not jkmr_app:
        logger.error(f"Could not find the '{JKMR_APP_NAME}' app")
        exit(1)

    if not site_visit_records_app:
        logger.error(f"Could not find the '{SITE_VISIT_RECORDS_APP_NAME}' app")
        exit(1)

    jkmr_records = get_app_records(jkmr_app)
    site_visit_records = get_app_records(site_visit_records_app)

    for jkmr_record in jkmr_records:
        jkmr_other_site_visits = get_jkmr_other_site_visits(jkmr_record)

        if len(jkmr_other_site_visits) == 0:
            logger.info("JKMR record has no 'Other' site visits, skipping...")
            continue

        matching_site_visit_record = find_matching_site_visit_record(
            jkmr_record, site_visit_records
        )

        if not matching_site_visit_record:
            logger.error(
                f"Could not find matching site visit record for JKMR record: {jkmr_record['id']}"
            )
            # TODO: Create a new site visit record
            # This record hasn't been transferred because all site visit records are of type "Other"?
            # TODO: Check if this is true ^
            exit(1)

        logger.info(
            f"Found matching site visit record for JKMR record: {jkmr_record['id']}"
        )
        logger.debug("Processing the site visit record update")
        process_site_visit_record_update(
            matching_site_visit_record, jkmr_other_site_visits
        )


if __name__ == "__main__":
    main()
