import argparse
import copy
import os
import time

from dotenv import load_dotenv
from fulcrum import Fulcrum
from tqdm import tqdm

load_dotenv()

parser = argparse.ArgumentParser(description="Update records.")
parser.add_argument(
    "--form_name", "-n", help="The name of the form of which to update records."
)
parser.add_argument(
    "--dry_run",
    "-d",
    action="store_true",
    help="Whether to run the script without updating records.",
)

args = parser.parse_args()

FULCRUM_API_KEY = os.getenv("FULCRUM_API_KEY")
FULCRUM = Fulcrum(FULCRUM_API_KEY)

FORM_NAME = args.form_name
DRY_RUN = args.dry_run


def get_updated_record(existing_record: dict):
    # =====================
    # This function is where you can update the record mappings
    # Provide your custom logic here
    # =====================

    # =====================
    # UPDATE: "Personnel details & qualifications" (key: "385f")
    # Wihin repeatable "Service Visit Records" (key: "3bdb")
    name_mappings = {
        "Jon Barton. CSJK. PCAQT. NPTC 499877, PA1 PA6AW": [
            '"Jon Barton. CSJK. PCAQT. NPTC 499877 (PA1',
            "Jon Barton",
        ],
        "Tom Clarke. PCAQT. NPTC 107028, PA1 PA6AW": ["Tom Clarke"],
        "Phil Cox. CSJK. PCAQT. NPTC 723725, PA1 PA6AW": [
            '"Phil Cox. CSJK. PCAQT. NPTC 723725 (PA1',
            "Phil Cox",
        ],
        "Matthew Patrycy. PCAQT. NPTC 353281 (PA1 PA6A)": [
            "Matthew Patrycy",
            "Matthew Patrycy ",
            "Matthew Patrycy NPTC",
            "Matthew Patrycy NPTC ",
            "Matthew Patrycy PCAQT ",
            "Matthew Patrycy PCAQT",
            "Matthew Patrycy. PCAQT.",
            '"Matthew Patrycy. PCAQT. NPTC 353281 (PA1',
        ],
        "David Soffe. PCAQT. NPTC 622432, PA1 PA6AW": ["David Soffe"],
        "Phil Walker. CSJK. PCAQT.  NPTC 410111, PA1 PA6AW": [
            '"Phil Walker. CSJK. PCAQT.  NPTC 410111 (PA1',
            "Phil Walker",
        ],
        "Paul Sweetman NPTC PA1 PA6": ["Paul Sweetman"],
        "James Erlam PA1 PA6 NPTC 88233": ["James Erlam"],
        None: [' PA6A)"', ' PA6/AW)"', " PA1 PA6", " NPTC 88233"],
    }

    if (
        "3bdb" not in existing_record["form_values"]
        or not existing_record["form_values"]["3bdb"]
    ):
        return False, existing_record

    repeatable = existing_record["form_values"]["3bdb"]

    for entry in repeatable:
        if "385f" not in entry["form_values"] or not entry["form_values"]["385f"]:
            continue

        selected_values_object = entry["form_values"]["385f"]
        updated_selected_values_object = copy.deepcopy(selected_values_object)

        for choice_value_object in [
            updated_selected_values_object["choice_values"],
            updated_selected_values_object["other_values"],
        ]:
            for i, choice in enumerate(choice_value_object):
                for key, value in name_mappings.items():
                    if choice in value:
                        choice_value_object[i] = key
                        break

        # Delete all values that equal None
        updated_selected_values_object["choice_values"] = [
            value for value in updated_selected_values_object["choice_values"] if value
        ]
        updated_selected_values_object["other_values"] = [
            value for value in updated_selected_values_object["other_values"] if value
        ]
        print(
            "Changing: "
            + str(selected_values_object)
            + " to: "
            + str(updated_selected_values_object)
        )

        # Replace the existing selected values object with the updated one
        entry["form_values"]["385f"] = updated_selected_values_object
    # =====================

    return True, existing_record


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
    if not DRY_RUN:
        FULCRUM.records.update(id, record)
        return True
    else:
        return False


def list_apps():
    apps = FULCRUM.forms.search()["forms"]
    print(f"Found {len(apps)} apps")
    return apps


def select_app(apps: list):
    print("Select an app to get records for:")

    for i, app in enumerate(apps):
        print(f"{i + 1}) {app['name']}")
        pass

    selection = input("Enter the number of the app you want to update records for: ")

    try:
        selection = int(selection)
    except ValueError:
        print("Invalid selection")
        exit(1)

    return apps[int(selection) - 1]


def get_app(name: str):
    apps = list_apps()
    for app in apps:
        if app["name"] == name:
            return app


def main():
    # If the app name is not passed, list all apps and get the user to select one
    app = None
    if not FORM_NAME:
        apps = list_apps()
        app = select_app(apps)
    else:
        app = get_app(FORM_NAME)

    # Get the form ID
    form_id = app["id"]

    # Get the records for the form
    records = FULCRUM.records.search(url_params={"form_id": form_id})["records"]

    progress_bar = tqdm(
        records,
        total=len(records),
        desc="Updating records",
    )

    # Loop for each key/value pair in the record mappings
    for record in progress_bar:
        updated, updated_record = get_updated_record(record)
        if not updated:
            continue

        update_made = update_record(updated_record["id"], {"record": updated_record})
        if update_made:
            progress_bar.set_description(f"Updated record: {updated_record['id']}")
        elif DRY_RUN and not update_made:
            progress_bar.set_description(
                f"Would have updated record: {updated_record['id']}"
            )
        else:
            progress_bar.set_description(
                f"Failed to update record: {updated_record['id']}"
            )

    progress_bar.close()
    print("Finished updating records")


if __name__ == "__main__":
    main()
