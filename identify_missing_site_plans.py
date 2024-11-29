import argparse
import csv
import difflib
import json
import logging
import os
import re
import shutil
import typing as t

import requests
from dotenv import load_dotenv

from fulcrum_helpers.helpers import FulcrumApp, find_key_code

load_dotenv()

# Arguments
parser = argparse.ArgumentParser(description="Update records.")
parser.add_argument(
    "--debug", help="Whether we should run in debug mode or not", action="store_true"
)

args = parser.parse_args()

FULCRUM_API_KEY = os.getenv("FULCRUM_API_KEY")
# Create the Fulcrum API object
FULCRUM = FulcrumApp(FULCRUM_API_KEY)

# Logging

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


def identify_missing_sv_site_plans():
    sv_app = FULCRUM.get_app("SITE VISIT RECORDS")
    site_plan_key = find_key_code(sv_app["elements"], "site_plans_attachments")
    site_plan_photo_key = find_key_code(sv_app["elements"], "site_plans")

    # Get the records
    sv_records = FULCRUM.get_app_records(sv_app)

    logger.info(f"Found {len(sv_records)} records")

    counter = {
        "missing_attachment": [],
        "missing_photo": [],
        "found_attachment": [],
        "found_photo": [],
    }

    for record in sv_records:
        # Get the site plan attachments
        site_plan_attachments = record["form_values"].get(site_plan_key, None)
        # Get the site plan photos
        site_plan_photos = record["form_values"].get(site_plan_photo_key, None)

        if not site_plan_attachments:
            logger.debug(f"No site plan attachments for record {record['id']}")
            counter["missing_attachment"].append(record["id"])
        else:
            logger.debug(f"Found site plan attachments for record {record['id']}")
            counter["found_attachment"].append(record["id"])

        if not site_plan_photos:
            logger.debug(f"No site plan photos for record {record['id']}")
            counter["missing_photo"].append(record["id"])
        else:
            logger.debug(f"Found site plan photos for record {record['id']}")
            counter["found_photo"].append(record["id"])

    # Print the results along with their percentages
    logger.info(
        f"Missing attachments: {len(counter['missing_attachment'])} ({len(counter['missing_attachment']) / len(sv_records) * 100:.2f}%)"
    )
    logger.info(
        f"Missing photos: {len(counter['missing_photo'])} ({len(counter['missing_photo']) / len(sv_records) * 100:.2f}%)"
    )

    logger.info(
        f"Found attachments: {len(counter['found_attachment'])} ({len(counter['found_attachment']) / len(sv_records) * 100:.2f}%)"
    )
    logger.info(
        f"Found photos: {len(counter['found_photo'])} ({len(counter['found_photo']) / len(sv_records) * 100:.2f}%)"
    )

    # Calculate the records that are missing both attachments and photos
    missing_both = set(counter["missing_attachment"]) & set(counter["missing_photo"])
    logger.info(
        f"Missing both: {len(missing_both)} ({len(missing_both) / len(sv_records) * 100:.2f}%)"
    )

    # Calculate the records that have both attachments and photos
    found_both = set(counter["found_attachment"]) & set(counter["found_photo"])
    logger.info(
        f"Found both: {len(found_both)} ({len(found_both) / len(sv_records) * 100:.2f}%)"
    )


def identify_missing_jkmr_site_plans():
    jkmr_app = FULCRUM.get_app("Japanese Knotweed Management Record (LEGACY)")
    site_plan_photo_key = find_key_code(jkmr_app["elements"], "site_plans")

    # Get the records
    jkmr_records = FULCRUM.get_app_records(jkmr_app)

    logger.info(f"Found {len(jkmr_records)} records")

    counter = {
        "missing_photo": [],
        "found_photo": [],
    }

    for record in jkmr_records:
        # Get the site plan photos
        site_plan_photos = record["form_values"].get(site_plan_photo_key, None)

        if not site_plan_photos:
            logger.debug(f"No site plan photos for record {record['id']}")
            counter["missing_photo"].append(record["id"])
        else:
            logger.debug(f"Found site plan photos for record {record['id']}")
            counter["found_photo"].append(record["id"])

    # Print the results along with their percentages
    logger.info(
        f"Missing photos: {len(counter['missing_photo'])} ({len(counter['missing_photo']) / len(jkmr_records) * 100:.2f}%)"
    )

    logger.info(
        f"Found photos: {len(counter['found_photo'])} ({len(counter['found_photo']) / len(jkmr_records) * 100:.2f}%)"
    )


def identify_missing_survey_site_plans():
    jkmr_app = FULCRUM.get_app("SURVEY")
    site_plan_photo_key = find_key_code(jkmr_app["elements"], "break_site_plans")

    # Get the records
    survey_records = FULCRUM.get_app_records(jkmr_app)

    logger.info(f"Found {len(survey_records)} records")

    counter = {
        "missing_photo": [],
        "found_photo": [],
    }

    for record in survey_records:
        # Get the site plan photos
        site_plan_photos = record["form_values"].get(site_plan_photo_key, None)

        if not site_plan_photos:
            logger.debug(f"No site plan photos for record {record['id']}")
            counter["missing_photo"].append(record["id"])
        else:
            logger.debug(f"Found site plan photos for record {record['id']}")
            counter["found_photo"].append(record["id"])

    # Print the results along with their percentages
    logger.info(
        f"Missing photos: {len(counter['missing_photo'])} ({len(counter['missing_photo']) / len(survey_records) * 100:.2f}%)"
    )

    logger.info(
        f"Found photos: {len(counter['found_photo'])} ({len(counter['found_photo']) / len(survey_records) * 100:.2f}%)"
    )


def main():
    print("Site visit records")
    identify_missing_sv_site_plans()

    print("\nJapanese Knotweed Management records")
    identify_missing_jkmr_site_plans()

    print("\nSurvey records")
    identify_missing_survey_site_plans()


if __name__ == "__main__":
    main()
