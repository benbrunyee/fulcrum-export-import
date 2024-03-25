#!/usr/bin/python3
"""
This script is used to go through an entire app's records.json file and find any data that is being hidden because of a conditional field.
We do this by checking whether the conditional is being met or not.
If the conditional to show the data is not met, we print the record ID, data_name of the field and the value of the field.
"""
import argparse
import builtins
import json
import logging
import os
import re
import sys
import typing as t

from dotenv import load_dotenv
from fulcrum import Fulcrum

load_dotenv()

parser = argparse.ArgumentParser(description="Find hidden data in an app")

# The name of the app to match on, not required
# App name is referenced as a "Form" in the Fulcrum API
parser.add_argument("--app-name", help="The name of the app to find hidden data in")
parser.add_argument(
    "--debug", help="The name of the app to find hidden data in", action="store_true"
)

# Parse the arguments
args = parser.parse_args()

APP_NAME = None
DEBUG = args.debug

# Get the Fulcrum API key from the environment variables
FULCRUM_API_KEY = os.getenv("FULCRUM_API_KEY")
# Create the Fulcrum API object
FULCRUM = Fulcrum(FULCRUM_API_KEY)

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
if args.app_name:
    APP_NAME = args.name


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


def select_app(apps: list):
    """
    Select an app from a list of apps
    """
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


def open(filename, mode):
    """
    Override builtin "open" function to open file but add filename to the global list of files
    This is so we can delete them later
    """
    global FILES_CREATED
    FILES_CREATED.append(filename)
    return builtins.open(filename, mode)


def get_app_records(app: dict):
    """
    Get the records of a specific app
    """
    records = FULCRUM.records.search({"form_id": app["id"]})["records"]
    return records


RecordWithHiddenData = t.TypedDict(
    "RecordWithHiddenData",
    {
        "record_id": str,
        "field_key": str,
        "data_name": str,
        "value": str,
        "reason": str,
    },
)

DictValue = t.TypedDict(
    "DictValue", {"choice_values": t.List[str], "other_values": t.List[str]}
)
PhotoValue = t.TypedDict(
    "PhotoValue",
    {
        "photo_id": str,
        "caption": str,
    },
)
AddressValue = t.TypedDict(
    "AddressValue",
    {
        "sub_admin_area": str,
        "locality": str,
        "admin_area": str,
        "postal_code": str,
        "country": str,
        "suite": str,
        "sub_thoroughfare": str,
        "thoroughfare": str,
    },
)


def traverse_search_record_for_key(
    record: dict, key: str
) -> t.Union[DictValue, PhotoValue, AddressValue, str, None]:
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


def flatten_app_elements(app: dict):
    elements = app["elements"]
    flattened_elements = []

    for element in elements:
        if element["type"] == "Section" or element["type"] == "Repeatable":
            flattened_elements += flatten_app_elements(element)
        else:
            flattened_elements.append(element)

    return flattened_elements


def get_data_name_field_key(app: dict, data_name: str):
    elements = flatten_app_elements(app)

    if args.debug:
        with open("elements.json", "w") as f:
            json.dump(elements, f, indent=4)
            logger.debug("Wrote elements to elements.json")

    for element in elements:
        if element["data_name"] == data_name:
            return element["key"]

    raise Exception(f"Could not find field with data name {data_name}")


def cleanup():
    """
    Delete all file that were created during the script
    """
    for filename in FILES_CREATED:
        os.remove(filename)


VisibleCondition = t.TypedDict(
    "VisibleCondition",
    {
        "field_key": str,
        "operator": t.Literal["equal_to", "not_equal_to", "is_not_empty"],
        "value": str,
    },
)

AppElement = t.TypedDict(
    "AppElement",
    {
        "key": str,
        "data_name": str,
        "visible_conditions_type": t.Literal["all", "any"],
        "visible_conditions": t.List[VisibleCondition],
    },
)


def find_fields_with_conditionals(app: dict) -> t.List[AppElement]:
    """
    Find all the fields in an app that have a conditional
    """
    fields_with_conditionals = []

    elements = flatten_app_elements(app)

    for element in elements:
        if (
            "visible_conditions" in element
            and element["visible_conditions"]
            and len(element["visible_conditions"]) > 0
        ):
            fields_with_conditionals.append(element)

    return fields_with_conditionals


def is_value_empty(value: t.Union[str, dict, None]) -> bool:
    """
    Check if a value is empty
    """
    # Values can be:
    # - A string
    # - A dict of structure DictValue
    # - A dict of structure PhotoValue
    # - A dict of structure AddressValue

    if value is None:
        return True

    if isinstance(value, str):
        return not value

    if isinstance(value, dict):
        if "choice_values" in value or "other_values" in value:
            if len(value["choice_values"]) == 0 and len(value["other_values"]) == 0:
                return True
            else:
                return False
        elif "photo_id" in value:
            return not value["photo_id"]
        elif "sub_admin_area" in value:
            return not any(value.values())


def flatten_field_choice_values(value: DictValue) -> str:
    """
    Flatten the choice values of a field to a string
    """
    if not value:
        return ""

    choice_values = value["choice_values"]
    other_values = value["other_values"]

    combined_values = ""

    if len(choice_values) > 0:
        combined_values += ",".join(choice_values)

    if len(other_values) > 0:
        combined_values += "," + ",".join(other_values)

    return combined_values


def main():
    """
    The main function of the script
    """

    # Get the app defined
    app = None

    if not APP_NAME:
        apps = list_apps()
        app = select_app(apps)
    else:
        app = get_app(APP_NAME)

    if args.debug:
        with open("app.json", "w") as f:
            json.dump(app, f, indent=4)
            logger.debug("Wrote app to app.json")

    # Using the app structure, we find what fields have a conditional
    fields_with_conditionals = find_fields_with_conditionals(app)

    if args.debug:
        with open("fields_with_conditionals.json", "w") as f:
            json.dump(fields_with_conditionals, f, indent=4)
            logger.debug(
                "Wrote fields with conditionals to fields_with_conditionals.json"
            )

    # Get the records of the app, we will search through these to find the hidden data
    records = get_app_records(app)

    if args.debug:
        with open("records.json", "w") as f:
            json.dump(records, f, indent=4)
            logger.debug("Wrote records to records.json")

    records_with_hidden_data = []  # type: t.List[RecordWithHiddenData]

    # Check each record
    for record in records:
        # Check each field with a conditional
        for field in fields_with_conditionals:
            field_key = field["key"]
            data_name = field["data_name"]
            # Get the value of the field
            value = traverse_search_record_for_key(record, field_key)

            # If the value is not empty, check if the visible conditions are met
            if not is_value_empty(value):
                visible_conditions = field["visible_conditions"]
                condition_type = field["visible_conditions_type"]

                condition_not_met_reason = None
                conditions_met_count = 0
                conditions_not_met_reasons = []  # type: t.List[str]

                # Check if the visible conditions are met
                for condition in visible_conditions:
                    condition_field_key = condition["field_key"]
                    condition_operator = condition["operator"]
                    condition_value = condition["value"]

                    # Get the value of the condition field
                    field_key_value = traverse_search_record_for_key(
                        record, condition_field_key
                    )

                    # Flatten the choice lists to strings (if they are applicable)
                    if (
                        isinstance(field_key_value, dict)
                        and "choice_values" in field_key_value
                        and "other_values" in field_key_value
                    ):
                        field_key_value = flatten_field_choice_values(field_key_value)

                    # Simulate the condition
                    if condition_operator == "equal_to":
                        if field_key_value == condition_value:
                            conditions_met_count += 1
                            continue
                    elif condition_operator == "not_equal_to":
                        if field_key_value != condition_value:
                            conditions_met_count += 1
                            continue
                    elif condition_operator == "is_not_empty":
                        if not is_value_empty(field_key_value):
                            conditions_met_count += 1
                            continue

                    # If the condition is not met, add the reason to the list
                    conditions_not_met_reasons.append(
                        f"Field {condition_field_key} with value {field_key_value} does not meet condition {condition_operator} {condition_value}"
                    )

                # If the condition type is "all" and not all conditions are met, or if the condition type is "any" and no conditions are met, add the record to the list
                if condition_type == "all":
                    if conditions_met_count != len(visible_conditions):
                        condition_not_met_reason = "Not all conditions met"
                elif condition_type == "any":
                    if conditions_met_count == 0:
                        condition_not_met_reason = "No conditions met"

                # If the condition is not met, add the record to the list
                if condition_not_met_reason:
                    records_with_hidden_data.append(
                        {
                            "record_id": record["id"],
                            "field_key": field_key,
                            "data_name": data_name,
                            "value": value,
                            # Join the reasons together
                            "reason": condition_not_met_reason
                            + " - "
                            + ", ".join(conditions_not_met_reasons),
                        }
                    )

    if args.debug:
        with open("records_with_hidden_data.json", "w") as f:
            json.dump(records_with_hidden_data, f, indent=4)
            logger.debug(
                "Wrote records with hidden data to records_with_hidden_data.json"
            )

    for record in records_with_hidden_data:
        logger.warning(
            f"Record ID: {record['record_id']} - Field: {record['data_name']} ({record['field_key']}) - Value: {record['value']} - Reason: {record['reason']}"
        )


if __name__ == "__main__":
    main()
