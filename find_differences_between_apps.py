#!/usr/bin/python3
"""
This script will highlight any differences between 2 Fulcrum apps
"""

import argparse
import json
import logging
import os
from copy import deepcopy
from enum import Enum

from dotenv import load_dotenv
from fulcrum import Fulcrum

# * Configuration
load_dotenv()

# * Arguments
parser = argparse.ArgumentParser()

# App name is referenced as a "Form" in the Fulcrum API
parser.add_argument("--app-1", help="The name of the first app to match on")
parser.add_argument("--app-2", help="The name of the second app to match on")
# Verbose argument
parser.add_argument(
    "--verbose", "-v", help="Print debug statements", action="store_true"
)

# Parse the arguments
args = parser.parse_args()


# * Set global variables
# Get the Fulcrum API key from the environment variables
FULCRUM_API_KEY = os.getenv("FULCRUM_API_KEY")
# Create the Fulcrum API object
FULCRUM = Fulcrum(FULCRUM_API_KEY)

APP_1_NAME = args.app_1
APP_2_NAME = args.app_2

TEMP_DIR_NAME = "differences_between_apps"

PARENT_ELEMENT_TYPES = [
    "Section",
    "Repeatable",
]

# * Configure logging
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
logger.setLevel(logging.DEBUG if args.verbose else logging.INFO)


# * Functions
def list_apps():
    apps = FULCRUM.forms.search()["forms"]
    logger.debug(f"Found {len(apps)} apps")
    return apps


def get_app(name: str):
    apps = list_apps()
    for app in apps:
        if app["name"] == name:
            return app


def select_app(apps: list, prompt: str = "Enter the number of the app: "):
    logger.info("Select an app:")

    for i, app in enumerate(apps):
        logger.info(f"{i + 1}) {app['name']}")
        pass

    selection = input(prompt)

    try:
        selection = int(selection)
    except ValueError:
        logger.error("Invalid selection")
        exit(1)

    return apps[int(selection) - 1]


def write_json_to_file(filename: str, data: dict):
    if not os.path.exists(TEMP_DIR_NAME):
        os.makedirs(TEMP_DIR_NAME)

    with open(os.path.join(TEMP_DIR_NAME, filename), "w") as f:
        json.dump(data, f, indent=2)


def clean_up():
    if os.path.exists(TEMP_DIR_NAME):
        os.rmdir(TEMP_DIR_NAME)


def get_both_apps():
    # If the app name is not passed, list all apps and get the user to select one
    apps = []

    app_1 = None
    if not APP_1_NAME or not APP_2_NAME:
        apps = list_apps()

    if not APP_1_NAME:
        app_1 = select_app(apps, prompt="Enter the number of the first app: ")
    else:
        app_1 = get_app(APP_1_NAME)

    app_2 = None
    if not APP_2_NAME:
        app_2 = select_app(apps, prompt="Enter the number of the second app: ")
    else:
        app_2 = get_app(APP_2_NAME)

    return app_1, app_2


class DifferenceType(str, Enum):
    MISSING_IN_APP_1 = "MISSING_IN_APP_1"
    MISSING_IN_APP_2 = "MISSING_IN_APP_2"
    DIFFERENT_IN_TYPE = "DIFFERENT_IN_TYPE"
    DIFFERENT_IN_CONDITIONAL = "DIFFERENT_IN_CONDITIONAL"
    DIFFERENT_IN_LABEL = "DIFFERENT_IN_LABEL"


def get_equivalent_element_by_data_name(data_name, elements):
    """
    Get the element with the same data name from the list of elements

    Parameters
    ----------
    data_name : str
        The data name of the element to find
    elements : list
        The list of elements to search through

    Returns
    -------
    element : dict
        The element with the same data name
    """
    for element in elements:
        if element["type"] in PARENT_ELEMENT_TYPES:
            # Get the children of this element
            children = element["elements"]
            element = get_equivalent_element_by_data_name(data_name, children)
            if element:
                return element
        else:
            # Check if this element is the one we are looking for
            if element["data_name"] == data_name:
                return element

    return None


def get_equivalent_element_by_label_text(label_text, elements):
    """
    Get the element with the same label text from the list of elements

    Parameters
    ----------
    label_text : str
        The label text of the element to find
    elements : list
        The list of elements to search through

    Returns
    -------
    element : dict
        The element with the same label text
    """
    for element in elements:
        if element["type"] in PARENT_ELEMENT_TYPES:
            # Get the children of this element
            children = element["elements"]
            element = get_equivalent_element_by_label_text(label_text, children)
            if element:
                return element
        else:
            # Check if this element is the one we are looking for
            if element["label"] == label_text:
                return element

    return None


def is_element_missing(element):
    return True if not element else False


def is_element_type_different(element_1, element_2):
    return True if element_1["type"] != element_2["type"] else False


def is_element_conditional_different(element_1, element_2):
    element_1_conditionals = deepcopy(element_1["visible_conditions"])
    element_2_conditionals = deepcopy(element_2["visible_conditions"])

    if not element_1_conditionals and not element_2_conditionals:
        # If both elements have no conditionals, they are the same
        return False
    elif not element_1_conditionals or not element_2_conditionals:
        # If one element has conditionals and the other doesn't, they are different
        return True

    # Both elements have conditionals, so compare them

    # Remove the "field_key" from each object in the conditional array
    # This is because the field_key is not relevant to the comparison
    for conditional in element_1_conditionals:
        del conditional["field_key"]

    for conditional in element_2_conditionals:
        del conditional["field_key"]

    has_different_conditionals = False
    # Compare the conditionals
    for conditional in element_1_conditionals:
        # Check if this conditional dict is in the other element
        if conditional not in element_2_conditionals:
            has_different_conditionals = True
            logger.info(
                f"Conditional {conditional} is not in element {element_2['data_name']}: {element_2_conditionals}"
            )
            break

    return has_different_conditionals


def compare_elements(
    app_1_elements, app_2_elements, missing_identifier: DifferenceType = None
):
    """
    Check if there are any elements missing from one app in the other

    Parameters
    ----------
    app_1_elements : list
        The elements of the first app
    app_2_elements : list
        The elements of the second app

    Returns
    -------
    missing_elements : list
        The elements that are missing from one app in the other
    """
    missing_elements = []
    for element in app_1_elements:
        difference_object = {
            "data_name": element["data_name"],
            "label": element["label"],
            # Not sure what difference type this is yet, hence no value
            "difference_type": None,
        }
        copy_of_difference_object = deepcopy(difference_object)

        if element["type"] in PARENT_ELEMENT_TYPES:
            # Get the children of this element
            children = element["elements"]
            missing_elements = missing_elements + compare_elements(
                children, app_2_elements, missing_identifier=missing_identifier
            )
        elif element["type"] == "Label":
            # Check if the label is different
            equivalent_element = get_equivalent_element_by_label_text(
                element["label"], app_2_elements
            )

            # If there is no equivalent element, then the label is different
            if not equivalent_element:
                missing_elements.append(
                    {
                        **copy_of_difference_object,
                        "difference_type": DifferenceType.DIFFERENT_IN_LABEL,
                    }
                )
                continue
        else:
            equivalent_element = get_equivalent_element_by_data_name(
                element["data_name"], app_2_elements
            )

            # If there is no equivalent element, add this element to the list of missing elements
            if not equivalent_element:
                missing_elements.append(
                    {
                        **copy_of_difference_object,
                        "difference_type": missing_identifier,
                    }
                )
                continue

            # Other checks
            if is_element_type_different(element, equivalent_element):
                missing_elements.append(
                    {
                        **copy_of_difference_object,
                        "difference_type": DifferenceType.DIFFERENT_IN_TYPE,
                    }
                )

            if is_element_conditional_different(element, equivalent_element):
                missing_elements.append(
                    {
                        **copy_of_difference_object,
                        "difference_type": DifferenceType.DIFFERENT_IN_CONDITIONAL,
                    }
                )

    return missing_elements


def remove_duplicates_from_list_of_dicts_based_on_data_name(list_of_dicts: list):
    """
    Remove duplicates from a list of dicts, based on the "data_name" key

    Parameters
    ----------
    list_of_dicts : list
        The list of dicts to remove duplicates from

    Returns
    -------
    list
        The list of dicts with duplicates removed
    """
    # Get the unique data names
    unique_data_names = set([x["data_name"] for x in list_of_dicts])

    # Create a new list of dicts with the unique data names
    new_list_of_dicts = []
    for data_name in unique_data_names:
        # Get the dicts with this data name
        dicts_with_this_data_name = [
            x for x in list_of_dicts if x["data_name"] == data_name
        ]

        is_already_in_new_list_of_dicts = False
        for new_dict in new_list_of_dicts:
            if new_dict["data_name"] == data_name:
                is_already_in_new_list_of_dicts = True
                break

        if not is_already_in_new_list_of_dicts:
            new_list_of_dicts.append(dicts_with_this_data_name[0])

    return new_list_of_dicts


def remove_duplicate_differences(list_of_dicts: list):
    """
    Remove duplicates from a list of dicts

    Parameters
    ----------
    list_of_dicts : list
        The list of dicts to remove duplicates from

    Returns
    -------
    list
        The list of dicts with duplicates removed
    """
    difference_types_to_remove_duplicates_from = [
        DifferenceType.DIFFERENT_IN_TYPE,
        DifferenceType.DIFFERENT_IN_LABEL,
        DifferenceType.DIFFERENT_IN_CONDITIONAL,
    ]

    # Loop through the difference types
    # Compare only the "difference_type" and "data_name" keys of each
    # object to identify duplicates
    new_list_of_dicts = []
    for difference_type in difference_types_to_remove_duplicates_from:
        # Get the dicts that have this difference type
        dicts_with_this_difference_type = [
            x for x in list_of_dicts if x["difference_type"] == difference_type
        ]

        # Remove duplicates from this list of dicts
        dicts_with_this_difference_type = (
            remove_duplicates_from_list_of_dicts_based_on_data_name(
                dicts_with_this_difference_type
            )
        )

        # Add these dicts to the new list
        new_list_of_dicts = new_list_of_dicts + dicts_with_this_difference_type

    return new_list_of_dicts


def find_differences_between_apps(app_1, app_2):
    """
    Find the differences between the 2 apps

    Parameters
    ----------
    app_1 : dict
        The first app to compare
    app_2 : dict
        The second app to compare

    Returns
    -------
    differences : dict
        The differences between the 2 apps. E.g.,
        [
            {
                "data_name": "{field_data_name: string}",
                "label": "{field_label: string}",
                "difference_type": "{difference_type: DifferenceType}",
            },
            {...},
            {...},
        ]
    """
    app_1_elements = app_1["elements"]
    app_2_elements = app_2["elements"]

    app_1_elements_with_differences = compare_elements(
        app_2_elements,
        app_1_elements,
        missing_identifier=DifferenceType.MISSING_IN_APP_1,
    )
    app_2_elements_with_differences = compare_elements(
        app_1_elements,
        app_2_elements,
        missing_identifier=DifferenceType.MISSING_IN_APP_2,
    )

    return remove_duplicate_differences(
        app_1_elements_with_differences + app_2_elements_with_differences
    )


# * Main
def main():
    app_1, app_2 = get_both_apps()
    write_json_to_file(f"app_1_{app_1['name']}.json", app_1)
    write_json_to_file(f"app_2_{app_2['name']}.json", app_2)

    differences = find_differences_between_apps(app_1, app_2)
    write_json_to_file("differences.json", differences)


if __name__ == "__main__":
    main()
