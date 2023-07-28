import argparse
import os
import time

from dotenv import load_dotenv
from fulcrum import Fulcrum
from tqdm import tqdm

load_dotenv()

parser = argparse.ArgumentParser(description="Update records.")
parser.add_argument(
    "--form_name", "-n", help="The name of the form to delete records from."
)
parser.add_argument(
    "--record_mappings_file", "-r", help="The file containing the record mappings."
)
args = parser.parse_args()

FULCRUM_API_KEY = os.getenv("FULCRUM_API_KEY")
FULCRUM = Fulcrum(FULCRUM_API_KEY)

FORM_NAME = args.form_name
RECORD_MAPPINGS_FILE = args.record_mappings_file


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
def delete_record(record_id: str):
    """
    Delete a record by ID
    """
    FULCRUM.records.delete(record_id)


def should_delete_record(record: dict):
    """
    Determine if a record should be deleted
    """
    return True


def main():
    target_form = None

    forms = FULCRUM.forms.search()

    for form in forms["forms"]:
        if form["name"] == FORM_NAME:
            target_form = form
            break

    if not target_form:
        print("Form not found")
        return

    all_form_records = FULCRUM.records.search(url_params={"form_id": target_form["id"]})

    progress_bar = tqdm(
        all_form_records["records"],
        total=len(all_form_records["records"]),
        desc="Deleting records",
    )

    for record in progress_bar:
        if should_delete_record(record):
            # delete_record(record["id"])
            progress_bar.set_description(f"Deleting record: {record['id']}")
        else:
            progress_bar.set_description(f"Skipping record: {record['id']}")


if __name__ == "__main__":
    main()
