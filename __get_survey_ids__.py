import argparse
import csv
import json
import os

from dotenv import load_dotenv
from fulcrum import Fulcrum

# 1. Take in an argument for the csv file location that has been uploaded to to the Fuclrum App
# 2. Query the Fulcrum API for a specific form (taken from arguments) and get all the records for that form
# 3. Loop through the records and get the record ID for each records that matches by the "job_id"
# 4. Note of any duplicates and print them out as errors

load_dotenv()

parser = argparse.ArgumentParser()
parser.add_argument(
    "--csv_file", help="The csv file that has been uploaded to Fulcrum", required=True)
parser.add_argument("--form_name", help="The Fulcrum form name", required=True)
parser.add_argument(
    "--job_id_key", help="The key for the job id column", required=True)

args = parser.parse_args()

CSV_FILE = args.csv_file
FORM_NAME = args.form_name
JOB_ID_KEY = args.job_id_key

FULCRUM_API_KEY = os.getenv('FULCRUM_API_KEY')
FULCRUM = Fulcrum(key=FULCRUM_API_KEY)


def get_fulcrum_form_id(form_name):
    print(f"Searching form: {form_name}")
    form = FULCRUM.forms.search(form_name)

    if not form or len(form["forms"]) == 0:
        raise Exception(f"No form with the name {form_name} was found")

    form_id = form["forms"][0]["id"]
    print(f"Found form ID: {form_id}")

    return form_id


def get_fulcrum_form_records(form_id):
    records = FULCRUM.records.search(
        url_params={'form_id': form_id, 'per_page': 2147483647})

    if not records:
        raise Exception(f"No records found for form {form_id}")

    return records["records"]


def read_csv_file(file):
    headers = []
    rows = []

    with open(file, 'r') as f:
        reader = csv.DictReader(f, strict=True)
        headers = [header for header in reader.fieldnames]

        rows = [row for row in reader]

    return headers, rows


def main():
    # Read the data
    form_id = get_fulcrum_form_id(FORM_NAME)
    uploaded_headers, uploaded_rows = read_csv_file(CSV_FILE)

    # Define the mappings
    mappings = {}
    row_obj = {}

    # Convert the rows to a dictionary for easier lookup
    for row in uploaded_rows:
        row_obj[row["pba_reference"]] = row

    # Loop through each of the fulcrum records
    for record in get_fulcrum_form_records(form_id):
        # Set commonly used variables
        record_id = record["id"]
        form_values = record["form_values"]

        # Check if the JOB_ID_KEY provided exists in the form values
        if JOB_ID_KEY not in form_values:
            print(f"Could not find a job id: {JOB_ID_KEY} for {record_id}")
            continue
        form_job_id = form_values[JOB_ID_KEY]

        # We will hit this if our locally saved csv file does not have the record that is in Fulcrum
        if form_job_id not in row_obj:
            print(
                f"Could not find a match for {record_id}, {form_job_id}")
            continue

        # We have a match if we've hit here
        print("Match")
        mappings[record["id"]] = row_obj[form_job_id]
        exit()

    print(json.dumps(mappings, indent=2))

    # Note of any duplicates
    seen_record_ids = set()
    for id, value in mappings.items():
        if id in seen_record_ids:
            print(
                f"Duplicate record found, {id}, {value['job_id']}")
            continue
        seen_record_ids.add(id)


if __name__ == "__main__":
    main()
