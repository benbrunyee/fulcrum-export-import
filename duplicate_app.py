import argparse
import logging
import os
import time

from dotenv import load_dotenv
from fulcrum import Fulcrum

load_dotenv()

parser = argparse.ArgumentParser()

# The name of the app to match on, not required
# App name is referenced as a "Form" in the Fulcrum API
parser.add_argument("--name", help="The name of the app to match on")
# A dry run argument for testing
parser.add_argument(
    "--dry-run", help="A dry run will not create a new app", action="store_true"
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

    logger.debug(f"App selected for duplication: {app}")

    # Duplicate the app
    duplicate_app(app)


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


def duplicate_app(app: dict):
    # Get the app name
    app_name = app["name"]

    # Get the app description
    app_description = app["description"]

    # Get the app elements
    app_elements = app["elements"]

    # Add the new app name postfix
    new_app_name = app_name + NEW_APP_POSTFIX

    # Create the new app
    new_app_id = None
    if not args.dry_run:
        new_app = FULCRUM.forms.create(
            {
                "form": {
                    "name": new_app_name,
                    "description": app_description,
                    "elements": app_elements,
                }
            }
        )

        # Get the new app id
        new_app_id = new_app["form"]["id"]

        logger.info(f"New app created: {new_app_name} ({new_app_id})")
    else:
        new_app_id = "dry_run"
        logger.info(f"New app created: {new_app_name} (dry run)")

    # Get the records from the existing app
    records = get_app_records(app["id"])

    # Create the new records
    logger.debug(f"Creating {len(records)} records for app: {new_app_name}")
    for record in records:
        create_app_record(record, new_app_id)


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
    # Get the record id
    record_id = record["id"]

    # Get the record form values
    record_form_values = record["form_values"]

    # Create the record
    if not args.dry_run:
        new_record = FULCRUM.records.create(
            {
                "record": {
                    "form_id": app_id,
                    "form_values": record_form_values,
                }
            }
        )

        # Get the new record id
        new_record_id = new_record["record"]["id"]

        logger.info(f"New record created: {new_record_id}")
    else:
        logger.info(f"New record created: {record_id} (dry run)")


if __name__ == "__main__":
    main()
