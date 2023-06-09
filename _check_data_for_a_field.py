#!/usr/bin/python3
"""
! DOES NOT WORK YET
This script will count how many records within an app have a value for a field
"""

import argparse
import json
import logging
import os

from dotenv import load_dotenv
from fulcrum import Fulcrum

load_dotenv()

parser = argparse.ArgumentParser()

# The name of the app to match on, not required
# App name is referenced as a "Form" in the Fulcrum API
parser.add_argument("--name", help="The name of the app to match on")
parser.add_argument(
    "--data-name",
    help="The data name of the field you would like to check",
    required=True,
)
# Debug argument
parser.add_argument("--debug", help="Print debug statements", action="store_true")

# Parse the arguments
args = parser.parse_args()

# Get the Fulcrum API key from the environment variables
FULCRUM_API_KEY = os.getenv("FULCRUM_API_KEY")
# Create the Fulcrum API object
FULCRUM = Fulcrum(FULCRUM_API_KEY)
# Store the name of the app to duplicate
APP_NAME = None
# The file containing the mappings
TARGET_DATA_NAME = args.data_name
# The postfix to add to the new app name
NEW_APP_POSTFIX = " - COPY (DO NOT USE)"

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

# If the name argument was passed, use it
if args.name:
    APP_NAME = args.name


def list_apps():
    apps = FULCRUM.forms.search()["forms"]
    logger.debug(f"Found {len(apps)} apps")
    return apps


def get_app(name: str):
    apps = list_apps()
    for app in apps:
        if app["name"] == name:
            return app


def select_app(apps: list):
    logger.info("Select an app:")

    for i, app in enumerate(apps):
        logger.info(f"{i + 1}) {app['name']}")
        pass

    selection = input("Enter the number of the app: ")

    try:
        selection = int(selection)
    except ValueError:
        logger.error("Invalid selection")
        exit(1)

    return apps[int(selection) - 1]


def get_all_fields_with_data_name(records: list, data_name: str):
    found_fields = []

    for record in records:
        if "data_name" in record and record["data_name"] == data_name:
            logger.debug(f"Found field with data name: {record}")
            found_fields.append(record)

        if "elements" in record and record["elements"] != None:
            found_fields.extend(get_all_fields_with_data_name(record, data_name))

    return found_fields


def get_app_records(app: dict):
    records = FULCRUM.records.search({"form_id": app["id"]})["records"]
    logger.info(f"Found {len(records)} records")
    logger.debug(f"Records: {json.dumps(records, indent=4)}")
    return records


def main():
    # If the app name is not passed, list all apps and get the user to select one
    app = None
    if not APP_NAME:
        apps = list_apps()
        app = select_app(apps)
    else:
        app = get_app(APP_NAME)

    logger.debug(f"App selected: {json.dumps(app, indent=4)}")

    app_records = get_app_records(app)
    fields_with_data_name = get_all_fields_with_data_name(app_records, TARGET_DATA_NAME)

    logger.info(f"Found {len(fields_with_data_name)} fields ")


if __name__ == "__main__":
    main()
