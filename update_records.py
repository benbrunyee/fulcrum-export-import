import argparse
import copy
import json
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


def update_name_mappings(existing_record: dict):
    """
    UPDATE: "Personnel details & qualifications" (key: "385f")
    Wihin repeatable "Service Visit Records" (key: "3bdb")
    """
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

    return True, existing_record


SURVEY_RECORDS = []


def get_record_from_survey_app(id: str):
    global SURVEY_RECORDS
    # Get the record from the "SURVEY" app (id: "8d430ae2-64cc-4b27-9b57-259afdbd8858")
    if len(SURVEY_RECORDS) == 0:
        SURVEY_RECORDS = FULCRUM.records.search(
            url_params={"form_id": "8d430ae2-64cc-4b27-9b57-259afdbd8858"}
        )["records"]

    for record in SURVEY_RECORDS:
        if record["id"] == id:
            return record

    return None


OLD_TO_NEW_MAPPING = None


def update_survey_record_links(existing_record: dict):
    """
    UPDATE: "Survey Record Links" (key: "96e4")

    SPECIFIC TO SITE VISIT RECORDS!

    1. Find the ID value for the "Survey Record Links"
    1. Check if the ID exists within the records for the "SURVEY" app
    1. If they do exist then don't perform any updates
    1. If they don't exist then check the "old_to_new_maping_IPMR.json" file for an ID mapping
    1. If there is not a mapping, then throw an error
    1. If there is a mapping, then update the ID value
    """
    global OLD_TO_NEW_MAPPING

    # Get the ID value for the "Survey Record Links" field
    survey_record_links_id = None
    if "96e4" in existing_record["form_values"]:
        survey_record_links_id = existing_record["form_values"]["96e4"]
    else:
        return False, existing_record

    if not survey_record_links_id or len(survey_record_links_id) == 0:
        # No survey record links to update
        print("No survey record links to update")
        return False, existing_record
    elif len(survey_record_links_id) > 1:
        raise Exception(
            f"Found multiple survey record links for record: {existing_record['id']}"
        )

    # Get the first record id

    survey_record_link_id = survey_record_links_id[0]["record_id"]

    does_record_exist_in_survey_app = bool(
        get_record_from_survey_app(survey_record_link_id)
    )

    if does_record_exist_in_survey_app:
        print("Record already exists in survey app")
        # No update required
        return False, existing_record

    # Check if there is a mapping for this ID
    if OLD_TO_NEW_MAPPING is None:
        with open("old_to_new_id_mapping_IPMR.json") as f:
            OLD_TO_NEW_MAPPING = json.load(f)

        with open("old_to_new_id_mapping_S.json") as f:
            OLD_TO_NEW_MAPPING.update(json.load(f))

    if survey_record_link_id not in OLD_TO_NEW_MAPPING:
        print(
            f"Could not find a mapping for ID: {survey_record_link_id} in 'old_to_new_id_mapping_IPMR.json' or 'old_to_new_id_mapping_S.json'"
        )
        with open("missing_mapping.txt", "a") as f:
            f.write(f"{survey_record_link_id}\n")
        return False, existing_record

    # Update the ID value
    print("Updating survey record link ID value")
    existing_record["form_values"]["96e4"][0]["record_id"] = OLD_TO_NEW_MAPPING[
        survey_record_link_id
    ]

    return True, existing_record


def update_repeatable_titles(existing_record: dict):
    """
    UPDATE: "{HIDE} Title" (key: "82f0")
    Within repeatable "Stand Details" key: "562d")

    Related fields:
        - "Plant Type" (key: "6a00")
        - "Stand Details" -> "Plant Name" (key: "4361")
        - "Stand Details" -> "Stand Number" (key: "30c0")

    The related fields are used to mimic the calculation field for the title
    """
    updated = False

    if (
        "562d" not in existing_record["form_values"]
        or not existing_record["form_values"]["562d"]
        or len(existing_record["form_values"]["562d"]) == 0
    ):
        return updated, existing_record

    if (
        "6a00" not in existing_record["form_values"]
        or not existing_record["form_values"]["6a00"]
    ):
        return updated, existing_record

    plant_type = existing_record["form_values"]["6a00"]["choice_values"][0]
    repeatable = existing_record["form_values"]["562d"]

    for i, stand in enumerate(repeatable):
        plant_name = (
            "4361" in existing_record["form_values"]
            and existing_record["form_values"]["4361"]
            or "Invasive Plant"
        )
        title_prefix = (
            plant_type == "Japanese Knotweed"
            and "Knotweed stand number"
            or f"{plant_name} Location"
        )

        stand_number = (
            "30c0" in stand["form_values"]
            and stand["form_values"]["30c0"]
            or f"{i + 1}"
        )

        if "82f0" in stand["form_values"]:
            # Title already exists so skip
            continue

        title = f"{title_prefix} {stand_number}"
        stand["form_values"]["82f0"] = title
        updated = True

    return updated, existing_record


LEGACY_RECORDS = None
LEGACY_SERVICE_VISIT_RECORDS = None


def update_site_visit_photos(existing_record: dict):
    """
    UPDATE:
        - "Photos" & captions (key: "e77c")
        - "Video" & captions (key: "8fb1")
        - "Notes" (key: "2d29")
    Within repeatable "Service Visit Records" key: "3bdb")

    Get the data from the legacy records.
    Legacy app name: "Invasive Plants Management Records (LEGACY)"
    Get data from under "Service Visit Records" (key: "6b8a"):
        - "Works photo record" (key: "35fb")
        - "Works video record" (key: "6821")
        - "Works notes" (key: "2227")
    Match records using the following data:
        - "Site address" (legacy key: "1b4b", new key: "c4ee")
        - "PBA REFERENCE" (legacy key: "c4ee", new key: "48ca")
    Match individual site visits using the following data:
        - "Service visit date" (legacy key: "8eaf", new key: "8eaf")
        - "Service visit time" (legacy key: "2a76", new key: "2a76")
        - "Service type" (legacy key: "a0ac", new key: "5c53")
        - "Visit category" (new app field == "Invasive Plants Management Record") (key: "4010")
        - "Record Type (new app field Invasive Plants == "Cut / Clearance / Excavation / Barrier / Other") (key: "1db0")
    """
    global LEGACY_RECORDS
    global LEGACY_SERVICE_VISIT_RECORDS

    updated = False

    if not LEGACY_RECORDS:
        LEGACY_RECORDS = get_app_records_by_app_name(
            "Invasive Plants Management Records (LEGACY)"
        )
        print(f"Found {len(LEGACY_RECORDS)} legacy records")

        LEGACY_SERVICE_VISIT_RECORDS = dict()
        for record in LEGACY_RECORDS:
            if "6b8a" not in record["form_values"] or not record["form_values"]["6b8a"]:
                continue

            LEGACY_SERVICE_VISIT_RECORDS[record["id"]] = record["form_values"]["6b8a"]

    service_visit_records = (
        "3bdb" in existing_record["form_values"]
        and existing_record["form_values"]["3bdb"]
        or []
    )

    if len(service_visit_records) == 0:
        return updated, existing_record

    for visit in service_visit_records:
        form_values = visit["form_values"]

        # If the "Visit category" does not exist for this visit or...
        # If the "Visit category" is not of the "Invasive Plants Management Record" category
        if (
            "4010" not in form_values
            or "Invasive Plants Management Record"
            not in form_values["4010"]["choice_values"]
        ):
            continue

        # If the "Record Type" does not exist for this visit or...
        # If the "Record Type" is not of the "Cut / Clearance / Excavation / Barrier / Other" category
        if (
            "1db0" not in form_values
            or "Cut / Clearance / Excavation / Barrier / Other"
            not in form_values["1db0"]["choice_values"]
        ):
            continue

        # If the service visit type is not of the "Other" category for Invasive plants
        if "5c53" not in form_values:
            continue

        # All checks have passed, this record needs fixing!

        # Get the legacy record that matches this record
        legacy_record = None

        for record in LEGACY_RECORDS:
            # TODO: Don't compare on ID, use fields to match
            if record["id"] == existing_record["id"]:
                legacy_record = record
                break

        # Get the legacy service visit entry that matches this record
        legacy_service_visit_entry = None
        if not legacy_record:
            raise Exception(
                f"Could not find legacy record for record: {existing_record['id']}"
            )
        for service_visit in LEGACY_SERVICE_VISIT_RECORDS[legacy_record["id"]]:
            # If the service visit date, time and type aren't present then skip
            if (
                "8eaf" not in service_visit["form_values"]
                or "2a76" not in service_visit["form_values"]
                or "a0ac" not in service_visit["form_values"]
            ):
                continue

            for k1, k2 in [["8eaf", "8eaf"], ["2a76", "2a76"], ["a0ac", "5c53"]]:
                if not do_record_key_values_match(service_visit, visit, k1, k2):
                    continue
                legacy_service_visit_entry = service_visit

        if not legacy_service_visit_entry:
            raise Exception(
                f"Could not find legacy service visit entry for record: {existing_record['id']}"
            )

    return updated, existing_record


def do_record_key_values_match(record_1: dict, record_2: dict, key_1: str, key_2: str):
    if key_1 not in record_1["form_values"] or key_2 not in record_2["form_values"]:
        return False
    elif record_1["form_values"][key_1] != record_2["form_values"][key_2]:
        return False
    else:
        return True


def get_app_records_by_app_name(app_name: str):
    app = get_app(app_name)
    return FULCRUM.records.search(url_params={"form_id": app["id"]})["records"]


def get_updated_record(existing_record: dict):
    # =====================
    # This function is where you can update the record mappings
    # Provide your custom logic here
    # =====================
    updated = False

    # updated, existing_record = update_name_mappings(existing_record)
    # updated, existing_record = update_survey_record_links(existing_record)
    # updated, existing_record = update_repeatable_titles(existing_record)
    updates, existing_record = update_site_visit_photos(existing_record)

    return updated, existing_record


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
