import argparse
import logging
import os
import typing as t

from dotenv import load_dotenv

from fulcrum_helpers.helpers import FulcrumApp, find_key_code
from fulcrum_helpers.types import RepeatableValue

load_dotenv()

parser = argparse.ArgumentParser(
    description="Import all the 'Other' visit types from the old JKMR app to the new SITE VISIT RECORDS app."
)
parser.add_argument(
    "--debug", help="Whether we should run in debug mode or not", action="store_true"
)

# Parse the arguments
args = parser.parse_args()

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

# Add a file handler to the logger
file_handler = logging.FileHandler(
    os.path.dirname(os.path.realpath(__file__)) + "/import_other_visits.log",
    mode="w+",
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(
    logging.Formatter(
        f"%(levelname)s::%(funcName)s::%(asctime)s - %(message)s", datefmt="%H:%M:%S"
    )
)
logger.addHandler(file_handler)

# Get the Fulcrum API key from the environment variables
FULCRUM_API_KEY = os.getenv("FULCRUM_API_KEY")
# Create the Fulcrum API object
FULCRUM = FulcrumApp(FULCRUM_API_KEY)


# MARK: Main
def main():
    sv_app = FULCRUM.get_app("SITE VISIT RECORDS")

    sv_records_key = find_key_code(sv_app["elements"], "service_visit_records")
    logger.info(f"SV records key: {sv_records_key}")

    sv_app_records = FULCRUM.get_app_records(sv_app)
    logger.info(f"SV app records: {len(sv_app_records)}")

    sv_vt_data_names = [
        "visit_type_japanese_knotweed_application_monitoring",
        "visit_type_japanese_knotweed_other",
        "visit_type_invasive_plants_application",
        "visit_type_invasive_plants_other",
        "visit_type_other_application",
        "visit_type_other_other",
    ]
    sv_vt_keys = [
        find_key_code(sv_app["elements"], vt_data_name)
        for vt_data_name in sv_vt_data_names
    ]

    for key in sv_vt_keys:
        if not key:
            logger.error(f"Key not found for {key}")
            exit(1)

    trackers = {
        "general_count": 0,
        "no_sv_records": [],
        "no_visit_type": [],
    }

    for app_record in sv_app_records:
        sv_records = app_record["form_values"].get(
            sv_records_key, []
        )  # type: RepeatableValue

        trackers["general_count"] += len(sv_records)

        if len(sv_records) == 0:
            trackers["no_sv_records"].append(app_record)
            continue

        missing_vt = False

        for sv_record in sv_records:
            vt_other_values = [
                sv_record["form_values"].get(vt_key, {}).get("other_values")
                for vt_key in sv_vt_keys
            ]

            vt_choice_values = [
                sv_record["form_values"].get(vt_key, {}).get("choice_values")
                for vt_key in sv_vt_keys
            ]

            vt_all = [
                x for vt in (vt_other_values + vt_choice_values) if vt for x in vt
            ]

            if len(vt_all) == 0:
                logger.debug(f"Missing visit type for {app_record["id"]}, {sv_record}")
                missing_vt = True

        if missing_vt:
            trackers["no_visit_type"].append(app_record)
            continue

    logger.info(
        "Summary: "
        + ", ".join(
            [
                f"{key}={len(trackers[key]) if isinstance(trackers[key], list) else trackers[key] }"
                for key in trackers
            ]
        )
    )


if __name__ == "__main__":
    main()
