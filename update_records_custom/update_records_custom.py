import argparse
import json
import os
import re

from dotenv import load_dotenv
from fulcrum import Fulcrum
from tqdm import tqdm

load_dotenv()

parser = argparse.ArgumentParser(description="Update records.")
parser.add_argument(
    "--dry_run",
    "-d",
    action="store_true",
    help="Whether to run the script without updating records.",
)


args = parser.parse_args()

FULCRUM_API_KEY = os.getenv("FULCRUM_API_KEY")
FULCRUM = Fulcrum(FULCRUM_API_KEY)

DRY_RUN = args.dry_run

if DRY_RUN:
    print("Running in dry run mode. No records will be updated.")


def get_records(form_name: str):
    """Get all records from a form."""
    all_forms = FULCRUM.forms.search()["forms"]

    form = [f for f in all_forms if f["name"] == form_name][0]
    records = FULCRUM.records.search(url_params={"form_id": form["id"]})["records"]
    return records


def get_repeatable_entries(record: dict, key: str):
    """Get all service visits for a record."""
    return record["form_values"].get(key, [])


def do_values_match(val_1, val_2):
    """Check if two values match."""
    # Check if falsy
    if not val_1 and not val_2:
        return True
    elif val_1 == val_2:
        return True
    else:
        return False


def does_site_address_match(site_address_1, site_address_2):
    """Check if two site addresses match."""
    keys_to_check = [
        "sub_thoroughfare",
        "thoroughfare",
        "postal_code",
        "locality",
        "country",
        "sub_admin_area",
        "suite",
    ]

    if not site_address_1 and not site_address_2:
        return True
    elif not site_address_1 or not site_address_2:
        return False

    for key in keys_to_check:
        if not do_values_match(site_address_1[key], site_address_2[key]):
            return False

    return True


def load_user_mapping():
    """Load the user mapping file."""
    if not os.path.exists("user_mapping.json"):
        with open("user_mapping.json", "w") as f:
            f.write("{}")

    user_mapping = {}
    with open("user_mapping.json", "r") as f:
        # Mappings are a dict where a legacy record ID points to a
        # current record ID
        user_mapping = json.load(f)

    return user_mapping


def get_single_matching_record(id: str, current_records: list):
    matching_records = [r for r in current_records if r["id"] == id]
    if len(matching_records) == 0:
        raise Exception(f"Could not find matching record in the new app: {id}.")
    elif len(matching_records) > 1:
        raise Exception(f"More than one matching record found: {id}.")
    else:
        return matching_records[0]


def get_matching_current_record(legacy_record: dict, current_records: list):
    """Get the current record that matches the legacy record."""

    legacy_record_id = legacy_record["id"]

    # If the user mapping file exists, load it
    # If the user mapping file does not exist, create it
    user_mapping = load_user_mapping()

    # Check if the legacy record ID is in the user mapping
    if legacy_record_id in user_mapping:
        # Return the current record that matches the user mapping
        return get_single_matching_record(
            user_mapping[legacy_record_id], current_records
        )

    # Get the pba ref from the legacy record
    legacy_pba_ref = legacy_record["form_values"].get("c4ee", None)

    # Get the site address from the legacy record
    legacy_site_address = legacy_record["form_values"].get("1b4b", None)

    # Loop through all the current records
    matching_records = []
    for current_record in current_records:
        # Check if the pba ref matches
        current_pba_ref = current_record["form_values"].get("c4ee", None)
        if not do_values_match(legacy_pba_ref, current_pba_ref):
            continue

        # Check if the site address matches
        current_site_address = current_record["form_values"].get("48ca", None)
        if not does_site_address_match(legacy_site_address, current_site_address):
            continue

        # If we get here, the record matches
        matching_records.append(current_record)

    # If there are no matching records, return None
    if not matching_records or len(matching_records) > 1:
        hint = ""
        if not matching_records:
            hint = "(no matching records found)"
        elif len(matching_records) > 1:
            hint = "(multiple matching records found)"

        # Get user input to manually find a matching record
        user_input_record_id = input(
            f"Could not find matching record {hint} "
            + f"in the new app: {legacy_record['id']} -> {legacy_record['form_values'].get('c4ee', 'No ID')}. "
            + 'Please enter the ID of the matching record ("n" to skip): '
        )

        if user_input_record_id == "n":
            return None

        # Save this user mapping to a file so we can use it in the future
        user_mapping[legacy_record_id] = user_input_record_id

        with open("user_mapping.json", "w") as f:
            json.dump(user_mapping, f, indent=2)

        return get_single_matching_record(user_input_record_id, current_records)

    # If there is more than one matching record then there is a problem
    if len(matching_records) > 1:
        confirm_or_fail(
            f"More than one matching record found: {', '.join([r['id'] for r in matching_records])}"
        )
        return matching_records

    # Return the matching record
    return matching_records[0]


def merge_choice_values(choice_values_1: dict, choice_values_2: dict):
    keys = [
        "choice_values",
        "other_values",
    ]

    merged_choice_values = {}

    for key in keys:
        merged_choice_values[key] = []

        if choice_values_1.get(key, None):
            merged_choice_values[key].extend(choice_values_1[key])

        if choice_values_2.get(key, None):
            merged_choice_values[key].extend(choice_values_2[key])

    return merged_choice_values


def does_choice_dict_include_dict_singular_value(
    choice_dict: dict, dict_singular_value: dict
):
    if not dict_singular_value and not choice_dict:
        return True

    dict_singular_value_values = get_choice_values(dict_singular_value)

    if not choice_dict and len(dict_singular_value_values) == 0:
        return True

    choice_dict_values = get_choice_values(choice_dict)

    if len(dict_singular_value_values) > 1:
        raise Exception("More than one value in dict singular value.")

    focus_value = dict_singular_value_values[0]

    for choice in choice_dict_values:
        choice_split = choice.split(",")

        if len(choice_split) > 1:
            for choice_split_value in choice_split:
                if (
                    focus_value == choice_split_value
                    or focus_value == choice_split_value.strip()
                ):
                    return True
        else:
            if focus_value == choice or focus_value == choice.strip():
                return True

    return False


def get_matching_current_service_visit(
    legacy_service_visit: dict, current_service_visits: list
):
    """Get the current service visit that matches the legacy service visit."""

    # Get the legacy service visit date
    legacy_service_visit_date = legacy_service_visit["form_values"].get("8eaf", None)

    # Get the legacy service visit time
    legacy_service_visit_time = legacy_service_visit["form_values"].get("2a76", None)

    # Get the legacy service type
    legacy_service_type = legacy_service_visit["form_values"].get("a0ac", None)

    for current_service_visit in current_service_visits:
        # Get the visit category
        current_service_visit_category = current_service_visit["form_values"].get(
            "4010", None
        )
        if (
            "Invasive Plants Management Record"
            not in current_service_visit_category["choice_values"]
        ):
            continue

        # Get the service visit record type
        current_service_visit_record_type = current_service_visit["form_values"].get(
            "1db0", None
        )
        if (
            "Cut / Clearance / Excavation / Barrier / Other"
            not in current_service_visit_record_type["choice_values"]
        ):
            continue

        # Get the current service visit date
        current_service_visit_date = current_service_visit["form_values"].get(
            "8eaf", None
        )
        if not do_values_match(legacy_service_visit_date, current_service_visit_date):
            continue

        # Get the current service visit time
        current_service_visit_time = current_service_visit["form_values"].get(
            "2a76", None
        )
        if not do_values_match(legacy_service_visit_time, current_service_visit_time):
            continue

        # Get the current service type
        current_service_type = current_service_visit["form_values"].get("5c53", None)
        # Since this is was split in the transfer, we simply check if the current value exists in the legacy values
        if not does_choice_dict_include_dict_singular_value(
            legacy_service_type, current_service_type
        ):
            continue

        # If we get here, the service visit matches
        return current_service_visit


def get_choice_values(choice_field: dict):
    keys = [
        "choice_values",
        "other_values",
    ]

    choice_values = []

    for key in keys:
        if choice_field.get(key, None):
            choice_values.extend(choice_field[key])

    return choice_values


def site_visit_contains_cut_clearance_activity(choice_field: dict):
    for choice in get_choice_values(choice_field):
        if re.match(r"Monitoring visit", choice):
            pass
        elif re.match(r"Herbicide treatment .*", choice):
            pass
        else:
            return True

    return False


def confirm_or_fail(message: str):
    confirmations = ["y", "yes"]

    user_input = ""
    if not DRY_RUN:
        user_input = input(f"{message}.\nContinue? (y/n): ")
    else:
        print(message)

    if user_input.lower() not in confirmations and not DRY_RUN:
        raise Exception("User aborted script.")

    print("Continuing as requested...")


def update_fields_from_priority_dict(
    legacy_service_visit: dict, current_service_visit: dict, priority_dict: dict
):
    did_update_take_place = False

    for field_key, field_keys_to_pull_data_from in priority_dict.items():
        for field_key_to_pull_data_from in field_keys_to_pull_data_from:
            value = legacy_service_visit["form_values"].get(field_key_to_pull_data_from)
            if value:
                if current_service_visit["form_values"].get(field_key, None):
                    # Print a warning since there is already a value
                    print(
                        f"Warning: {field_key} already has a value: {current_service_visit['form_values'][field_key]}. Value will be overwritten."
                    )
                current_service_visit["form_values"][field_key] = value
                did_update_take_place = True
                break

    return did_update_take_place, current_service_visit


def update_service_visit(legacy_service_visit: dict, current_service_visit: dict):
    did_update_take_place = False

    # Check if there is any data in the following fields
    fields_to_check_for_data = {
        "notes": "2d29",
        "photos": "e77c",
        "video": "8fb1",
    }

    update_required = False
    for field_key in fields_to_check_for_data.values():
        value = current_service_visit["form_values"].get(field_key, None)

        # There is already a value, so we don't need to update
        if not value or len(value) == 0:
            break

        update_required = True

    if not update_required:
        return did_update_take_place, current_service_visit

    # Update the fields
    # The last value in the list is the highest priority
    fields_to_pull_data_from = {
        "notes": ["2227", "2d29"],
        "photos": ["35fb", "e77c"],
        "video": ["6821", "8fb1"],
    }
    did_update_take_place, current_service_visit = update_fields_from_priority_dict(
        legacy_service_visit, current_service_visit, fields_to_pull_data_from
    )

    return did_update_take_place, current_service_visit


if os.path.exists("missing_site_visits.txt"):
    os.remove("missing_site_visits.txt")


def log_missing_site_visit(parent_record_id: str, legacy_service_visit_id: str):
    with open("missing_site_visits.txt", "a") as f:
        f.write(f"{legacy_service_visit_id}\n")


if os.path.exists("missing_records.txt"):
    os.remove("missing_records.txt")

if os.path.exists("multiple_record_matches.txt"):
    os.remove("multiple_record_matches.txt")


def main():
    # Get all the legacy records
    legacy_records = get_records("Invasive Plants Management Records (LEGACY)")

    # Get all the current records
    current_records = get_records("SITE VISIT RECORDS")

    # Find the matching data entries
    current_record = None
    current_service_visit = None

    # Loop through all the legacy records
    updated_records_count = []
    updated_service_visit_entries = []
    for legacy_record in legacy_records:
        # Get matching current record
        current_record = get_matching_current_record(legacy_record, current_records)
        if not current_record:
            confirm_or_fail(
                f"Could not find matching record in the new app: {legacy_record['id']} -> {legacy_record['form_values'].get('c4ee', 'No ID')}."
            )
            with open("missing_records.txt", "a") as f:
                f.write(
                    f"{legacy_record['id']} -> {legacy_record['form_values'].get('c4ee', 'No ID')}\n"
                )
            continue
        if isinstance(current_record, list) and len(current_record) > 1:
            confirm_or_fail(
                f"More than one matching record found: {legacy_record['id']} -> {legacy_record['form_values'].get('c4ee', 'No ID')}."
            )
            with open("multiple_record_matches.txt", "a") as f:
                f.write(
                    f"{legacy_record['id']} -> {legacy_record['form_values'].get('c4ee', 'No ID')}\n"
                )
            continue

        # "6b8a" is the key for the legacy service visits repeatable
        legacy_service_visits = get_repeatable_entries(legacy_record, "6b8a")

        # "3bdb" is the key for the current service visits repeatable
        current_service_visits = get_repeatable_entries(current_record, "3bdb")

        did_update_take_place = False
        for legacy_service_visit in legacy_service_visits:
            if legacy_service_visit["id"] == "2ea13fa1-ecd9-4af8-9f1e-8140cc92f078":
                pass

            # Are we interested in this site visit
            if legacy_service_visit["form_values"].get(
                "a0ac", None
            ) and not site_visit_contains_cut_clearance_activity(
                legacy_service_visit["form_values"]["a0ac"]
            ):
                print(
                    f"Skipping site visit of type: {','.join(get_choice_values(legacy_service_visit['form_values']['a0ac']))}"
                )
                continue

            # Get matching current service visit
            current_service_visit = get_matching_current_service_visit(
                legacy_service_visit, current_service_visits
            )

            # If there is no matching current service visit then something has gone wrong
            # in the transfer
            if not current_service_visit:
                log_missing_site_visit(legacy_record["id"], legacy_service_visit["id"])
                confirm_or_fail(
                    f"Could not find matching service visit in the new app: {legacy_service_visit['id']}."
                )
                continue

            # Perform updates
            (
                did_service_visit_update_take_place,
                current_service_visit,
            ) = update_service_visit(legacy_service_visit, current_service_visit)

            if did_service_visit_update_take_place:
                updated_service_visit_entries.append(current_record["id"])
                did_update_take_place = True

        if did_update_take_place:
            updated_records_count.append(
                legacy_record["id"] + " -> " + current_record["id"]
            )
            # if not DRY_RUN:
            #     FULCRUM.records.update(current_service_visit)

    print(f"Updated {len(updated_service_visit_entries)} service visit entries.")
    print(f"Updated {len(updated_records_count)} records")

    with open("updated_service_visit_entries.txt", "w") as f:
        f.write("\n".join(updated_service_visit_entries))

    with open("updated_records.txt", "w") as f:
        f.write("\n".join(updated_records_count))


if __name__ == "__main__":
    main()
