import argparse
import json
import os
import time

from dotenv import load_dotenv
from fulcrum import Fulcrum
from tqdm import tqdm

load_dotenv()

parser = argparse.ArgumentParser(description="Update records.")
parser.add_argument(
    "--record_mappings_file", "-r", help="The file containing the record mappings."
)

args = parser.parse_args()

FULCRUM_API_KEY = os.getenv("FULCRUM_API_KEY")
FULCRUM = Fulcrum(FULCRUM_API_KEY)


def traverse_search_record_for_key(record: dict, key: str):
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


def get_updated_record(old_record: dict, new_record: dict):
    # =====================
    # Update the "Plant Name" field (old key: "6008", new key: "4361")
    # This can be found within the repeatable section "Stand Details" (old key: "d93c", new key: "562d")

    # Find this repeatable section (by key) within the old record
    # Loop through each repeatable and match to the new record equivalent
    # Do this by comparing all the values for each field in the repeatable
    # If there is no match, throw an error
    # If there is a match, we update the repeatable to include an key/value pair
    # of { "6008": {old_record_6008_object} }

    # If the "Plant Name" field (key: "6008") cannot be found within the old record
    # we can skip this. This is because, there will not be a key if there was no
    # value set for this field.

    old_d93c_value = traverse_search_record_for_key(old_record, "d93c")
    if not old_d93c_value:
        print(f"No d93c value found for old record ID: {old_record['id']}")
        print("Skipping this record")
        return new_record

    new_562d_value = traverse_search_record_for_key(new_record, "562d")
    if not new_562d_value:
        print(f"No 562d value found for new record ID: {new_record['id']}")
        raise Exception("This section should always exist")

    # Loop through each repeatable in the new record
    for i, new_repeatable in enumerate(new_562d_value):
        old_6008_value = traverse_search_record_for_key(
            old_d93c_value[i]["form_values"], "6008"
        )

        if not old_6008_value:
            print(f"No 6008 value found for old record ID: {old_record['id']}")
            print("Skipping this repeatable")
            continue

        # Add the "4361" new key equivalent to the repeatable
        # Set it to the old "6008" value
        new_repeatable["form_values"]["4361"] = old_6008_value

    return new_record
    # =====================


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
def update_record(id: str, record: dict):
    FULCRUM.records.update(id, record)
    print(f"Updated record: {record['record']['id']}")


def main():
    record_mappings = {}

    with open(args.record_mappings_file) as f:
        record_mappings = json.load(f)

    progress_bar = tqdm(
        record_mappings.items(),
        total=len(record_mappings),
        desc="Updating records",
    )

    # Loop for each key/value pair in the record mappings
    for old_record_id, new_record_id in progress_bar:
        old_record = FULCRUM.records.find(old_record_id)["record"]
        new_record = FULCRUM.records.find(new_record_id)["record"]

        progress_bar.set_description(f"Updating record: {old_record_id}")
        updated_record = get_updated_record(old_record, new_record)
        update_record(updated_record["id"], {"record": updated_record})

    progress_bar.close()
    print("Finished updating records")


if __name__ == "__main__":
    main()
