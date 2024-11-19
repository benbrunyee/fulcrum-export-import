import argparse
import copy
import json
import logging
import os
import re
import time

from deepdiff import DeepDiff
from dotenv import load_dotenv
from fulcrum import Fulcrum
from tqdm import tqdm

from fulcrum_helpers.helpers import FulcrumApp, find_key_code
from fulcrum_helpers.types import PhotoValue

load_dotenv()

parser = argparse.ArgumentParser(description="Update records.")
parser.add_argument(
    "--dry_run",
    "-d",
    action="store_true",
    help="Whether to run the script without updating records.",
)
parser.add_argument(
    "--debug", help="Whether we should run in debug mode or not", action="store_true"
)

args = parser.parse_args()

FULCRUM_API_KEY = os.getenv("FULCRUM_API_KEY")
# Create the Fulcrum API object
FULCRUM = FulcrumApp(FULCRUM_API_KEY)

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

DRY_RUN = args.dry_run

if DRY_RUN:
    logger.info("Running in dry run mode. No records will be updated.")


def main():
    # Get the key for the site plan attachments
    sv_app = FULCRUM.get_app("SITE VISIT RECORDS")
    site_plan_key = find_key_code(sv_app["elements"], "site_plans_attachments")
    logger.info(f"Site plan key: {site_plan_key}")

    # Get the records
    sv_records = FULCRUM.get_app_records(sv_app)

    logger.info(f"Found {len(sv_records)} records")

    attachment_count = 0

    for record in sv_records:
        # Get the site plan attachments
        site_plan_attachments = record["form_values"].get(site_plan_key, None)

        if not site_plan_attachments:
            logger.debug(f"No site plan attachments for record {record['id']}")
            continue

        logger.debug(f"Record ID: {record["id"]}")
        logger.debug(f"Found site plan attachments: {site_plan_attachments}")

        # Get the site plan attachments
        attachments = FULCRUM.get_record_attachments(record["id"])

        if attachments.status_code != 200:
            logger.error(f"Failed to get attachment {attachments}")
            continue

        attachments_json = attachments.json()
        logger.info(attachments_json)

        if attachments_json["total_count"] == 0:
            logger.warning(f"No attachments for record {record['id']}")
            continue

        attachment_count += attachments_json["total_count"]

    logger.info(f"Found {attachment_count} attachments")
    debug_attachments()


def debug_attachments():
    attachment_count = 0
    attachments = FULCRUM.list_attachments()
    attachments_json = attachments.json()

    logger.info(f"Found {len(attachments_json)} attachments")

    attachment_count = 0

    for attachment in attachments_json.values():
        attachment_count += attachment["count"]

    attachments_flattened = [
        y for y in (x["attachments"] for x in attachments_json.values())
    ]

    logger.debug(f"Flattened attachments count: {len(attachments_flattened)}")
    logger.debug(f"Attachment count: {attachment_count}")


if __name__ == "__main__":
    main()
