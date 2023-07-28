#!/usr/bin/python3
"""
This script checks whether a field mapping has been applied to a section/field
that is conditionally rendered. If so, it will need to be manually checked to
see whether this field mapping is still applicable.
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
    "--target-mappings", help="The file containing the mappings", required=True
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
MAPPING_FILE = args.target_mappings
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


def get_mappings():
    with open(MAPPING_FILE) as f:
        mappings = json.load(f)

    return mappings


def get_section_elements(elements: list):
    section_elements = []
    for element in elements:
        if "elements" in element and element["elements"] != None:
            section_elements.extend(get_section_elements(element["elements"]))
        else:
            section_elements.append(element)

    return section_elements


def get_conditional_elements(elements: list):
    # If the element is a section/repeatable (has "elements" key), check the elements
    # If any of the parent elements are conditionally rendered, add them to the list and don't check the children
    # since they will be conditionally rendered as well
    # If the element is a field, check the "visible_conditions" key

    conditional_elements = []
    for element in elements:
        if "visible_conditions" in element and element["visible_conditions"] != None:
            element_copy = element.copy()
            children_elements = (
                element_copy.pop("elements") if "elements" in element_copy else None
            )

            conditional_elements.append(element_copy)
            if children_elements != None:
                # Extend with all the elements in the section since they will be conditionally rendered as well
                conditional_elements.extend(get_section_elements(children_elements))
        elif "elements" in element and element["elements"] != None:
            conditional_elements.extend(get_conditional_elements(element["elements"]))

    return conditional_elements


def main():
    # If the app name is not passed, list all apps and get the user to select one
    app = None
    if not APP_NAME:
        apps = list_apps()
        app = select_app(apps)
    else:
        app = get_app(APP_NAME)

    logger.debug(f"App selected: {app}")

    mappings = get_mappings()
    mapping_values = mappings.values()

    app_elements = app["elements"]
    conditional_elements = get_conditional_elements(app_elements)

    data_names = {}
    for element in conditional_elements:
        data_names[element["data_name"]] = element["label"]

    # Find intersection of conditional elements and mapping values
    intersection = set(data_names.keys()).intersection(mapping_values)

    if len(intersection) > 0:
        logger.warning(
            f"Found {len(intersection)} conditional elements that have been mapped"
        )

        logger.warning(f"Please check whether these mappings are still applicable:")
        for element in intersection:
            logger.warning(f"{element} = {data_names[element]}")


if __name__ == "__main__":
    main()
