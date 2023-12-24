import argparse
import json
import logging
import os

from dotenv import load_dotenv
from fulcrum import Fulcrum

load_dotenv()

parser = argparse.ArgumentParser(description="Save a record to Fulcrum.")
parser.add_argument("--record", "-r", help="The record file.")
parser.add_argument(
    "--form_name", "-n", help="The name of the form to import data into."
)
parser.add_argument("--debug", help="Print debug statements", action="store_true")

args = parser.parse_args()

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

# Constants

RECORD = args.record
FORM_NAME = args.form_name

FULCRUM_API_KEY = os.getenv("FULCRUM_API_KEY")
FULCRUM = Fulcrum(FULCRUM_API_KEY)

if not RECORD or not os.path.exists(RECORD):
    logger.info("No record file provided.")
    exit(1)

if not FORM_NAME:
    logger.info("No form ID provided.")
    exit(1)


def list_apps():
    apps = FULCRUM.forms.search()["forms"]
    logger.debug(f"Found {len(apps)} apps")
    return apps


def get_app(name: str):
    apps = list_apps()
    for app in apps:
        if app["name"] == name:
            return app


def main():
    record_json = None

    app = get_app(FORM_NAME)

    if not app:
        logger.error("App not found.")
        exit(1)

    with open(args.record) as json_file:
        record_json = json.load(json_file)["record"]

    if not record_json:
        logger.error("Record file is empty.")
        exit(1)

    new_record = FULCRUM.records.create(
        {
            "record": {
                "form_id": app["id"],
                "latitude": record_json["latitude"],
                "longitude": record_json["longitude"],
                "status": record_json["status"],
                "form_values": record_json["form_values"],
            }
        }
    )

    new_record_id = new_record["record"]["id"] if "id" in new_record["record"] else None

    if not new_record_id:
        logger.error("Failed to create record.")
        exit(1)

    logger.info("Record created with ID: " + new_record_id)


if __name__ == "__main__":
    main()
