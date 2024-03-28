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

from fulcrum_types.types import Record

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
    },
    "SITE_VISIT_RECORDS": {
        # Match records on values of these keys
        "job_id": "c4ee",
        "site_address": "48ca",
        # End of matching keys
        "service_visit_records": "3bdb",
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
                jkmr_record["form_values"].get(KEY_NAMES["JKMR"]["site_address"], None),
                site_visit_record["form_values"].get(
                    KEY_NAMES["SITE_VISIT_RECORDS"]["site_address"], None
                ),
            ],
        ]

        # If any of the values are emtpy, warn and skip
        # This is because we cannot compare empty values as they most likely
        # will match and cause issues
        jkmr_values = [value[0] for value in comparissons]
        are_all_jkmr_values_truthy = all(jkmr_values)

        if not are_all_jkmr_values_truthy:
            logger.error(f"Value from JKMR record is empty: {comparissons}")
            # Return None here because we won't be able to find a match with empty values in the
            # JKMR record
            return None

        site_visit_values = [value[1] for value in comparissons]
        are_all_site_visit_values_truthy = all(site_visit_values)

        if not are_all_site_visit_values_truthy:
            logger.debug(
                f"Skipping comparisson for this site visit record: {site_visit_job_id} as one of the values is empty: {comparissons}"
            )
            continue

        matches = True

        # Check if all the comparissons match
        for values in comparissons:
            # If the values are not the same, then it does not match
            if values[0] != values[1]:
                matches = False

        if matches:
            return site_visit_record

    logger.warn(
        f"Could not find a matching site visit record for JKMR record: {jkmr_record['id']} - {jkmr_job_id}"
    )
    return None


def get_jkmr_other_site_visits(jkmr_record: Record) -> t.List[Record]:
    """
    Get all the "Other" site visit records from a JKMR record
    """
    other_site_visits = jkmr_record["form_values"].get(
        KEY_NAMES["JKMR"]["other_visit_repeatable"], None
    )

    if other_site_visits == None:
        logger.error(
            f"Could not find 'Other' site visits for JKMR record: {jkmr_record['id']}"
        )
        exit(1)

    logger.debug(f"Other site visits: {other_site_visits}")
    logger.info(
        f"Found {len(other_site_visits)} 'Other' site visits for JKMR record: {jkmr_record['id']}"
    )

    return other_site_visits


def process_site_visit_record_update(site_visit_record: Record, jkmr_record: Record):
    """
    Processes the update of a site visit record
    """
    jkmr_other_site_visits = get_jkmr_other_site_visits(jkmr_record)

    if len(jkmr_other_site_visits) == 0:
        logger.info("JKMR record has no 'Other' site visits, not processing")
        return


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
        matching_site_visit_record = find_matching_site_visit_record(
            jkmr_record, site_visit_records
        )

        if not matching_site_visit_record:
            logger.error(
                f"Could not find matching site visit record for JKMR record: {jkmr_record['id']}"
            )
            exit(1)

        logger.info(
            f"Found matching site visit record for JKMR record: {jkmr_record['id']}"
        )
        logger.debug("Processing the site visit record update")
        process_site_visit_record_update(matching_site_visit_record, jkmr_record)


if __name__ == "__main__":
    main()
