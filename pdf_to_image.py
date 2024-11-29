"""
Converts site plan PDF attachments in the SITE VISIT RECORDS app into images
"""

import argparse
import json
import logging
import os
import shutil
import typing as t

import pymupdf
import requests
from dotenv import load_dotenv

from fulcrum_helpers.helpers import FulcrumApp, find_key_code

load_dotenv()

parser = argparse.ArgumentParser(description="Update records.")
parser.add_argument(
    "--dry_run",
    "-d",
    action="store_true",
    help="Whether to run the script without updating records.",
)
parser.add_argument(
    "--debug", help="Whether we should run in debug mode or not", action="store_true"
)

args = parser.parse_args()

FULCRUM_API_KEY = os.getenv("FULCRUM_API_KEY")
# Create the Fulcrum API object
FULCRUM = FulcrumApp(FULCRUM_API_KEY)

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

DRY_RUN = args.dry_run

if DRY_RUN:
    logger.info("Running in dry run mode. No records will be updated.")


def main():
    # Get the key for the site plan attachments
    sv_app = FULCRUM.get_app("SITE VISIT RECORDS")
    site_plan_key = find_key_code(sv_app["elements"], "site_plans_attachments")
    job_id_key = find_key_code(sv_app["elements"], "job_id")
    logger.info(f"Site plan key: {site_plan_key}")

    # Get the records
    sv_records = FULCRUM.get_app_records(sv_app)

    logger.info(f"Found {len(sv_records)} records")

    attachment_error_count = 0
    attachment_urls = {}

    for record in sv_records:
        # Get the site plan attachments
        site_plan_attachments = record["form_values"].get(site_plan_key, None)
        job_id = record["form_values"].get(job_id_key, None)

        if not job_id:
            logger.debug(f"No job ID for record {record['id']}")
            continue

        if not site_plan_attachments:
            logger.debug(f"No site plan attachments for record {record['id']}")
            continue

        logger.debug(f"Record ID: {record["id"]}")
        logger.debug(f"Found site plan attachments: {site_plan_attachments}")

        # Create a directory for the record ID
        if not os.path.exists(f"pdf_images/{record['id']}"):
            os.makedirs(f"pdf_images/{record['id']}")

        # Create an info.json file with the job ID
        with open(f"pdf_images/{record['id']}/info.json", "w") as f:
            info = {
                "job_id": job_id,
                "record_id": record["id"],
            }
            f.write(json.dumps(info))

        for sp_attachment in site_plan_attachments:
            try:
                attachment = FULCRUM.get_attachment(sp_attachment["attachment_id"])
                download_url = attachment["download_url"]
                logger.debug(f"Download URL: {download_url}")

                attachment_urls[job_id] = download_url
            except Exception as e:
                logger.error(f"Error getting attachment: {e}")
                attachment_error_count += 1

    logger.info(f"Found {len(attachment_urls)} attachments")
    logger.warning(f"Found {attachment_error_count} errors")
    logger.debug(f"Attachment URLs: {attachment_urls}")

    convert_pdfs_to_images(attachment_urls)


def convert_pdfs_to_images(entries: t.Dict[str, str]):
    """
    Convert the PDFs to images
    """

    # Recreate the pdf_image directory
    if os.path.exists("pdf_images"):
        shutil.rmtree("pdf_images")
    os.makedirs("pdf_images/original")
    os.makedirs("pdf_images/processed")

    for job_id, download_url in entries.items():
        logger.info(f"Downloading attachment for job ID {job_id}")
        response = requests.get(download_url)
        with open(f"pdf_images/original/{job_id}.pdf", "wb") as f:
            f.write(response.content)

        # Convert the PDF to an image
        pdf = pymupdf.open(f"pdf_images/original/{job_id}.pdf")
        for page in pdf:
            pix = page.get_pixmap()
            pix.save(f"pdf_images/processed/{job_id}_{page.number}.png")

    logger.info("Finished downloading attachments")


if __name__ == "__main__":
    main()
