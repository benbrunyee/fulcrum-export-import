import argparse
import copy
import json
import logging
import os
import shutil

from dotenv import load_dotenv

from fulcrum_helpers.helpers import FulcrumApp, find_key_code

load_dotenv()

parser = argparse.ArgumentParser(
    description="Import all the 'Other' visit types from the old JKMR app to the new SITE VISIT RECORDS app."
)
parser.add_argument(
    "--debug", help="Whether we should run in debug mode or not", action="store_true"
)
parser.add_argument(
    "--no-confirmation",
    help="Whether user confirmation is required for each record update",
    action="store_true",
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
    # Get the apps
    jkmr_app = FULCRUM.get_app("Japanese Knotweed Management Record (LEGACY)")
    sv_app = FULCRUM.get_app("SITE VISIT RECORDS")

    # Get the key for the "Site Photo (property)" data name
    jkmr_site_photo_key = find_key_code(jkmr_app["elements"], "site_photo_property")
    logger.info(f"JKMR Site Photo (property) key: {jkmr_site_photo_key}")
    sv_site_photo_key = find_key_code(sv_app["elements"], "site_photos_property")
    logger.info(f"SV Site Photo (property) key: {sv_site_photo_key}")

    # Get the reference key
    jkmr_reference_key = find_key_code(jkmr_app["elements"], "pba_reference")
    logger.info(f"JKMR Reference key: {jkmr_reference_key}")
    sv_reference_key = find_key_code(sv_app["elements"], "job_id")
    logger.info(f"SV Reference key: {sv_reference_key}")

    # Get the records
    jkmr_records = FULCRUM.get_app_records(jkmr_app)
    sv_records = FULCRUM.get_app_records(sv_app)

    # Get all the records that have at least 1 site photo
    jkmr_records_with_site_photo = [
        record
        for record in jkmr_records
        if record["form_values"].get(jkmr_site_photo_key, None)
    ]

    logger.info(
        f"Found {len(jkmr_records_with_site_photo)} JKMR records with site photos"
    )

    # Get a count of all the references
    jkmr_references = [
        record["form_values"][jkmr_reference_key]
        for record in jkmr_records_with_site_photo
    ]
    jkmr_references.sort()

    # Keep track of the records skipped
    skipped_record_refs = []

    trackers = {
        "record_not_found": [],
        "site_photo_not_found": [],
        "skipped_count": 0,
    }

    # Convert the records into a dictionary with the reference as the key
    jkmr_records_with_site_photo_dict = {}

    for record in jkmr_records_with_site_photo:
        ref = record["form_values"][jkmr_reference_key]

        # Check the number of records with the same reference
        first_index = jkmr_references.index(ref)
        next_index = first_index + 1

        if ref in skipped_record_refs:
            logger.warning(f"Skipping record with reference: {ref}")
            trackers["skipped_count"] += 1
            continue
        elif (
            first_index != -1
            and len(jkmr_references) - 1 != first_index
            and jkmr_references[next_index] == ref
        ):
            logger.warning(f"Duplicate reference: {ref}")

            # Check with the user if they want to skip the record
            response = input("Skip record? (y/n): ")
            if response.lower() == "y":
                skipped_record_refs.append(ref)
                trackers["skipped_count"] += 1
                continue
            else:
                exit(1)

        jkmr_records_with_site_photo_dict[ref] = {
            "record": record,
            "site_photos": record["form_values"][jkmr_site_photo_key],
        }

    # Loop through the site photo records and check if the sv record has a site photo
    for ref in jkmr_records_with_site_photo_dict:
        sv_record = next(
            (
                sv_record
                for sv_record in sv_records
                if sv_record["form_values"].get(sv_reference_key, None) == ref
            ),
            None,
        )

        if sv_record is None:
            logger.warning(f"Record not found for reference: {ref}")
            trackers["record_not_found"].append(sv_record)
            continue

        if not sv_record["form_values"].get(sv_site_photo_key, None):
            logger.warning(f"Site photo not found for reference: {ref}")
            trackers["site_photo_not_found"].append(sv_record)
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

    # Delete the differences directory if it exists
    if os.path.exists("differences"):
        shutil.rmtree("differences")

    # Create the differences directory
    os.mkdir("differences")

    # Update the SV records with the site photos
    for ref in jkmr_records_with_site_photo_dict:
        sv_record = next(
            (
                sv_record
                for sv_record in sv_records
                if sv_record["form_values"].get(sv_reference_key, None) == ref
            ),
            None,
        )

        if sv_record is None:
            continue

        site_photos = jkmr_records_with_site_photo_dict[ref]["site_photos"]
        new_sv_record = copy.deepcopy(sv_record)
        new_sv_record["form_values"][sv_site_photo_key] = site_photos

        # Write the differences
        safe_ref = (
            ref.replace("/", "-").replace(" ", "_").replace(":", "-").replace("\\", "-")
        )
        with open(f"differences/{safe_ref}-old.json", "w") as f:
            f.write(json.dumps(sv_record, indent=2))

        with open(f"differences/{safe_ref}-new.json", "w") as f:
            f.write(json.dumps(new_sv_record, indent=2))

        # Ask for confirmation
        if not args.no_confirmation:
            logger.info(f"Old: {sv_record}")
            logger.info(f"New: {new_sv_record}")
            response = input("Update record? (y/n): ")
            if response.lower() != "y":
                continue

        # Update the record
        FULCRUM.update_fulcrum_record(
            sv_record["id"],
            new_sv_record,
        )

        logger.info(f"Updated record for reference: {ref}")


if __name__ == "__main__":
    main()
