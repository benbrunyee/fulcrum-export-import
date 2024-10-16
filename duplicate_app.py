import argparse
import copy
import json
import logging
import os
import random
import time

from dotenv import load_dotenv
from fulcrum import Fulcrum
from tqdm import tqdm

load_dotenv()

parser = argparse.ArgumentParser()

# The name of the app to match on, not required
# App name is referenced as a "Form" in the Fulcrum API
parser.add_argument("--name", help="The name of the app to match on")
# A dry run argument for testing
parser.add_argument(
    "--dry-run", help="A dry run will not create a new app", action="store_true"
)
parser.add_argument(
    "--yes", "-y", help="Automatically answer yes to all prompts", action="store_true"
)
# Debug argument
parser.add_argument("--debug", help="Print debug statements", action="store_true")
parser.add_argument("--postfix", help="The postfix to add to the new app name")
parser.add_argument(
    "--progressive",
    help="Progressively duplicate the app. Helpful when an existing duplication has failed.",
    action="store_true",
)
# Parse the arguments
args = parser.parse_args()

# Get the Fulcrum API key from the environment variables
FULCRUM_API_KEY = os.getenv("FULCRUM_API_KEY")
# Create the Fulcrum API object
FULCRUM = Fulcrum(FULCRUM_API_KEY)
# Store the name of the app to duplicate
APP_NAME = None
# The postfix to add to the new app name
NEW_APP_POSTFIX = args.postfix or " - COPY (DO NOT USE)"
# If the user has confirmed all prompts
CONFIRMED = args.yes
# If the user wants to progressively duplicate the app
PROGRESSIVE = args.progressive

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

if args.dry_run:
    logger.info("Dry run enabled")


def main():
    # If the app name is not passed, list all apps and get the user to select one
    app = None
    if not APP_NAME:
        apps = list_apps()
        app = select_app(apps)
    else:
        app = get_app(APP_NAME)

    # Write to temp file if in debug mode
    if args.debug:
        logger.debug(f"Writing app to file: {app}")
        with open(".app.json", "w") as f:
            json.dump(app, f, indent=2)

    # Get confirmation from the user
    confirmation = ""
    if not CONFIRMED:
        confirmation = input(
            f"Are you sure you want to duplicate the app: {app['name']}? (y/N): "
        )

    # Delete the temp file if in debug mode
    if args.debug:
        os.remove(".app.json")

    # If the user does not confirm, exit
    if confirmation.lower() != "y" and not CONFIRMED:
        logger.info("Exiting")
        exit(0)

    app_already_exists = False
    if PROGRESSIVE:
        app_already_exists = does_app_exist(app)

    # Duplicate the app
    duplicate_app(app, app_already_exists=app_already_exists)

    logger.info("Done")


def does_app_exist(app):
    # Get the app name
    app_name = app["name"]

    # Add the new app name postfix
    new_app_name = app_name + NEW_APP_POSTFIX

    # Get the apps
    apps = list_apps()

    # Check if the app exists
    for app in apps:
        if app["name"] == new_app_name:
            return True

    return False


def list_apps():
    apps = FULCRUM.forms.search()["forms"]
    logger.debug(f"Found {len(apps)} apps")
    return apps


def select_app(apps: list):
    logger.info("Select an app to duplicate:")

    for i, app in enumerate(apps):
        logger.info(f"{i + 1}) {app['name']}")
        pass

    selection = input("Enter the number of the app you want to duplicate: ")

    try:
        selection = int(selection)
    except ValueError:
        logger.error("Invalid selection")
        exit(1)

    return apps[int(selection) - 1]


def get_app(name: str):
    apps = list_apps()
    for app in apps:
        if app["name"] == name:
            return app


def duplicate_app(app: dict, app_already_exists: bool = False):
    # Get the app name
    app_name = app["name"]

    # Get the app description
    app_description = app["description"]

    # Get the app elements
    app_elements = app["elements"]

    # Get the app title field keys
    app_title_field_keys = app["title_field_keys"]

    # Add the new app name postfix
    new_app_name = app_name + NEW_APP_POSTFIX

    # Status field
    status_field = app["status_field"]

    # Create the new app
    new_app_id = None
    if not args.dry_run:
        if not app_already_exists:
            new_app = FULCRUM.forms.create(
                {
                    "form": {
                        "name": new_app_name,
                        "title_field_keys": app_title_field_keys,
                        "description": app_description,
                        "status_field": status_field,
                        "elements": app_elements,
                        "hidden_on_dashboard": True,
                    },
                }
            )

            # Get the new app id
            new_app_id = new_app["form"]["id"]

            logger.info(f"New app created: {new_app_name} ({new_app_id})")
        else:
            # Get the apps
            existing_apps = list_apps()

            # Check if the app exists
            for existing_app in existing_apps:
                if existing_app["name"] == new_app_name:
                    new_app_id = existing_app["id"]
                    break

            if not new_app_id:
                logger.error(f"Failed to find new app: {new_app_name}")
                exit(1)

            logger.info(f"New app already exists: {new_app_name} ({new_app_id})")
    else:
        new_app_id = "dry_run"
        logger.info(f"New app created: {new_app_name} (dry run)")

    # Get the records from the existing app
    records = get_app_records(app["id"])

    if args.debug:
        logger.debug(f"Writing records to file: {records}")
        with open(".records.json", "w") as f:
            json.dump(records, f, indent=2)

    # Get the percentage of records to duplicate
    record_duplication_percentage = 100
    if not CONFIRMED:
        record_duplication_percentage = input(
            f"What percentage of records do you want to duplicate ({len(records)} records)? (100%): "
        )

    # If the user does not enter a percentage, default to 100
    if not record_duplication_percentage or CONFIRMED:
        record_duplication_percentage = 100
    else:
        try:
            record_duplication_percentage = int(record_duplication_percentage)
        except ValueError:
            logger.error("Invalid percentage")
            exit(1)

    # Shuffle the records
    logger.debug("Shuffling records")
    random.shuffle(records)

    # Get the number of records to duplicate
    number_of_records_to_duplicate = int(
        (record_duplication_percentage / 100) * len(records)
    )
    logger.debug(
        f"Number of records to duplicate: {number_of_records_to_duplicate}/{len(records)} ({record_duplication_percentage}%)"
    )

    # Get the records to duplicate
    records_to_duplicate = records[:number_of_records_to_duplicate]

    # Create the new records
    logger.debug(
        f"Creating {len(records_to_duplicate)} records for app: {new_app_name}"
    )
    progress_records = tqdm(
        records_to_duplicate,
        total=number_of_records_to_duplicate,
        desc="Records created",
    )
    for record in progress_records:
        if PROGRESSIVE:
            record_exists = does_record_exist(new_app_id, record["id"])

            if record_exists:
                progress_records.set_description(
                    f"Record already exists: {record['id']}"
                )
                continue

        record = correct_record(app, record)
        progress_records.set_description(f"Creating record: {record['id']}")

        try:
            create_app_record(record, new_app_id)
        except Exception as e:
            logger.error(f"Failed to create record: {record['id']}", exc_info=e)
            exit(1)
    progress_records.close()


def does_record_exist(app_id: str, record_id: str):
    # Open a file that maps the old record id to the new record id
    try:
        with open(".record_map.json", "r") as f:
            record_map = json.load(f)
    except FileNotFoundError:
        record_map = {}

    # Check if the record exists
    if record_id in record_map:
        return True

    return False


def correct_record(app: dict, record: dict):
    """
    Corrects the record to be created
    """
    # Deep copy the record
    corrected_record = copy.deepcopy(record)

    # Get all valid status values
    valid_status_values = [x["value"] for x in app["status_field"]["choices"]]

    # Ensure that the record status is valid
    if not record["status"] or record["status"] == "":
        # Set it to the default status
        corrected_record["status"] = app["status_field"]["default_value"]
    elif record["status"] not in valid_status_values:
        # Leave it blank if it is invalid otherwise this will cause an error
        # when creating the record
        corrected_record["status"] = ""

    return corrected_record


def get_app_records(app_id: str):
    logger.debug(f"Getting records for app: {app_id}")
    records = FULCRUM.records.search({"form_id": app_id})["records"]
    logger.debug(f"Found {len(records)} records")
    return records


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
def create_app_record(record: dict, app_id: str):
    record_id = record["id"]
    record_form_values = record["form_values"]
    record_status = record["status"]

    # GPS coordinates
    record_longitude = record["longitude"]
    record_latitude = record["latitude"]

    # Create the record
    if not args.dry_run:
        new_record = FULCRUM.records.create(
            {
                "record": {
                    "form_id": app_id,
                    "status": record_status,
                    "form_values": record_form_values,
                    "longitude": record_longitude,
                    "latitude": record_latitude,
                }
            }
        )

        # Get the new record id
        new_record_id = (
            new_record["record"]["id"] if "id" in new_record["record"] else None
        )

        if not new_record_id:
            logger.error(f"Failed to create record: {record_id}")
            raise Exception(f"Could not find new record id in: {new_record}")

        logger.debug(f"New record created: {new_record_id}")
    else:
        logger.debug(f"New record created: {record_id} (dry run)")

    # Open a file that maps the old record id to the new record id
    if PROGRESSIVE:
        try:
            with open(".record_map.json", "r") as f:
                record_map = json.load(f)
        except FileNotFoundError:
            record_map = {}

        # Add the mapping to the file
        record_map[record_id] = new_record_id

        # Write the file
        with open(".record_map.json", "w") as f:
            json.dump(record_map, f, indent=2)


if __name__ == "__main__":
    main()
