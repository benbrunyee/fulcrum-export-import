#!/usr/bin/python3
"""
This script will count how many records within an app have a value for a field
"""

import argparse
import builtins
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

# The list of files created
FILES_CREATED = []

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


def get_app_records(app: dict):
    records = FULCRUM.records.search({"form_id": app["id"]})["records"]
    return records


def flatten_app_elements(app: dict):
    elements = app["elements"]
    flattened_elements = []

    for element in elements:
        if element["type"] == "Section" or element["type"] == "Repeatable":
            flattened_elements += flatten_app_elements(element)
        else:
            flattened_elements.append(element)

    return flattened_elements


def traverse_search_record_for_key(record: dict, key: str):
    """
    Recursively search a record for a key
    """

    found_record = None

    # If the record is a list, iterate over it
    if isinstance(record, list):
        for item in record:
            found_record = traverse_search_record_for_key(item, key)
            if found_record:
                break
    # If the record is a dict, check if it has the key
    elif isinstance(record, dict):
        if key in record:
            return record[key]
        else:
            for v in record.values():
                found_record = traverse_search_record_for_key(v, key)
                if found_record:
                    break
    return found_record


def get_data_name_field_key(app: dict, data_name: str):
    elements = flatten_app_elements(app)

    if args.debug:
        with open("elements.json", "w") as f:
            f.write(json.dumps(elements, indent=4))
            logger.debug("Wrote elements to elements.json")

    for element in elements:
        if element["data_name"] == data_name:
            return element["key"]

    raise Exception(f"Could not find field with data name {data_name}")


def open(filename, mode):
    """
    Override builtin "open" function to open file but add filename to the global list of files
    This is so we can delete them later
    """
    global FILES_CREATED
    FILES_CREATED.append(filename)
    return builtins.open(filename, mode)


def cleanup():
    # Delete all file that were created during the script
    for filename in FILES_CREATED:
        os.remove(filename)


def main():
    # If the app name is not passed, list all apps and get the user to select one
    app = None
    if not APP_NAME:
        apps = list_apps()
        app = select_app(apps)
    else:
        app = get_app(APP_NAME)

    if args.debug:
        with open("app.json", "w") as f:
            f.write(json.dumps(app, indent=4))
            logger.debug("Wrote app to app.json")

    # Get the key of the field with the data name
    field_key = get_data_name_field_key(app, TARGET_DATA_NAME)
    logger.info(f"Data name field key: {field_key}")

    app_records = get_app_records(app)
    logger.info(f"Found {len(app_records)} records")

    if args.debug:
        with open("app_records.json", "w") as f:
            f.write(json.dumps(app_records, indent=4))
            logger.debug("Wrote app records to app_records.json")

    target_values_with_key = []

    for target_value in app_records:
        record_with_key = traverse_search_record_for_key(target_value, field_key)
        if record_with_key:
            target_values_with_key.append(target_value)

    logger.info(f"Found {len(target_values_with_key)} records with key: {field_key}")

    if args.debug:
        with open("target_values_with_key.json", "w") as f:
            f.write(json.dumps(target_values_with_key, indent=4))
            logger.debug("Wrote target values with key to target_values_with_key.json")

    # Count how many records have each value
    # A value can a dict with at least 1 value in the "choice_values" key or "other_values" key
    # or a direct value
    value_counts = 0
    for target_value in target_values_with_key:
        has_choice_value_set = False
        has_other_value_set = False

        if isinstance(target_value, dict):
            if "choice_values" in target_value:
                if len(target_value["choice_values"]) > 0:
                    has_choice_value_set = True

            if "other_values" in target_value:
                if len(target_value["other_values"]) > 0:
                    has_other_value_set = True

        if has_choice_value_set or has_other_value_set or target_value:
            value_counts += 1

    logger.info(
        f"Found {value_counts} records with a value for {field_key} ({TARGET_DATA_NAME})"
    )

    # Clean up
    cleanup()


if __name__ == "__main__":
    main()
