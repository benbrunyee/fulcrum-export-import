import argparse
import csv
import json
import os
import time
from datetime import datetime

from dotenv import load_dotenv
from fulcrum import Fulcrum

load_dotenv()

parser = argparse.ArgumentParser(
    description='Import data from a CSV file into Fulcrum.')
parser.add_argument(
    '--form_name', "-n", help='The name of the form to import data into.')
parser.add_argument(
    '--source_dir', "-s", help='The directory containing the CSV files to import.')
parser.add_argument(
    "--type", help="The type of import to perform.", type=str, required=True)

args = parser.parse_args()


# Constants

FORM_NAME = args.form_name
SOURCE_DIR = args.source_dir
FULCRUM_API_KEY = os.getenv('FULCRUM_API_KEY')

TYPE = args.type

FULCRUM = Fulcrum(FULCRUM_API_KEY)

READ_REPEATABLES = {}
PROJECT_IDS = {}
USER_IDS = {}

PARENT_TO_LATEST_SURVEY_ID = "parent_to_latest_survey.json"


# Util

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


def save_first_record(form_id):
    records = FULCRUM.records.search(url_params={
        'form_id': form_id})['records']

    with open("record.json", "w") as f:
        json.dump(records[0], f, indent=2)


def save_form(target_form):
    with open("form.json", "w") as f:
        json.dump(target_form, f, indent=2)


def convert_to_epoch(string):
    date_format = "%Y-%m-%d %H:%M:%S %Z"
    date_obj = datetime.strptime(string, date_format)

    # Convert the datetime object to seconds since the epoch
    seconds_since_epoch = date_obj.timestamp()

    return seconds_since_epoch

# Main


def read_csv(file_path):
    """Read a csv file and return a list of rows"""
    with open(file_path, "r") as f:
        reader = csv.DictReader(f)
        return list(reader)


def get_csv_files(dir):
    return [f for f in os.listdir(dir) if os.path.isfile(
        os.path.join(dir, f)) and f.endswith(".csv")]


# Rate limited for 4000 calls per hour (actual limit is 5000/h but we want to be safe)
@rate_limited(4000 / 3600)
def upload_records(records):
    for record in records:
        id_mapping = {}
        res = None
        retry_count = 0

        while retry_count < 3:
            try:
                res = FULCRUM.records.create(record)

                if "error" in res:
                    raise Exception("Error creating record")

                break
            except Exception:
                print("Error creating record. Retrying in 1 second...")
                time.sleep(1)
                retry_count += 1

        if not res:
            print(f"Failed to create record {record['record']['fulcrum_id']}")
            continue

        print(res['record']['id'] + ' created.')

        if TYPE == "survey":
            # Update the IMPORT_MAPPING_FILE file to map the old record_id to the new record_id
            if os.path.exists(PARENT_TO_LATEST_SURVEY_ID):
                with open(PARENT_TO_LATEST_SURVEY_ID, "r") as f:
                    id_mapping = json.load(f)

            if record["record"]["fulcrum_parent_id_not_used"] not in id_mapping:
                id_mapping[record['record']['fulcrum_parent_id_not_used']] = {
                    'id': res['record']['id'],
                    'date': res['record']['created_at']
                }
            else:
                existing_date = id_mapping[record['record']
                                           ['fulcrum_parent_id_not_used']]['date']
                date_format = "%Y-%m-%dT%H:%M:%SZ"
                existing_date_obj = datetime.strptime(
                    existing_date, date_format)

                new_date = res['record']['created_at']
                new_date_obj = datetime.strptime(new_date, date_format)

                # If the new record is newer than the existing record then update the mapping
                if new_date_obj > existing_date_obj:
                    id_mapping[record['record']['fulcrum_parent_id_not_used']] = {
                        'id': res['record']['id'],
                        'date': res['record']['created_at']
                    }

            with open(PARENT_TO_LATEST_SURVEY_ID, "w") as f:
                json.dump(id_mapping, f, indent=2)


# {element} is the repeatable element
def read_repeatable_data(parent_id, element):
    global READ_REPEATABLES

    # The data_name of the repeatable element
    data_name = element["data_name"]

    # If the file named "{data_name}.csv" does not exist then return an empty list
    if not os.path.exists(os.path.join(SOURCE_DIR, data_name + ".csv")):
        return []

    # We do this so we don't read the CSV file multiple times
    rows = []
    if data_name not in READ_REPEATABLES:
        rows = read_csv(os.path.join(SOURCE_DIR, data_name + ".csv"))
        READ_REPEATABLES[data_name] = rows
    else:
        rows = READ_REPEATABLES[data_name]

    flattened_elements = list(flatten(element["elements"]))

    # TODO: Filter rows based on the fulcrum_parent_id column
    rows = list(
        filter(lambda row: row["fulcrum_parent_id"] == parent_id, rows))

    return create_repeatable_objects(flattened_elements, rows, parent_id)


def handle_text_field(value, element):
    if not value:
        return value

    if "format" not in element:
        return value

    if element["format"] == "decimal":
        # We don't actually convert since the API will do that for us
        try:
            float(value)
        except Exception:
            print("Could not convert value to float: " + value)
            return None
    elif element["format"] == "integer":
        try:
            int(value)
        except Exception:
            print("Could not convert value to int: " + str(value))
            return None

    return value


def save_records(records):
    with open("all_records.json", "w") as f:
        json.dump(records, f, indent=2)


def get_record_link(record_id, value):
    # If there is no value then this is likely to be a new field that should be populated
    # We can find the record_id for this field by looking at the sa export,
    # matching on a row and then grabbing the fulcrum_id

    # If there is a value or we are doing a survey import, use the value
    if value or TYPE == "survey":
        return [{"record_id": v} for v in value.split(",")] if value else []

    # We match based on the mapping file that was created during the SA import process (using this script)
    with open(PARENT_TO_LATEST_SURVEY_ID, "r") as f:
        mapping = json.load(f)

        if record_id not in mapping:
            print("Could not find a match for " + record_id)
            return []

        return [{"record_id": mapping[record_id]['id']}]


def create_value_structure(element, row, record_id=None):
    el_type = element["type"]
    data_name = element["data_name"]

    value = row[data_name] if data_name in row else None
    other_value = row[data_name +
                      "_other"] if data_name + "_other" in row else None
    caption_value = row[data_name +
                        "_caption"] if data_name + "_caption" in row else None

    skip_types = [
        "Section"
    ]

    if el_type in skip_types:
        return None

    object_types = {
        "ClassificationField": {"other_values": other_value.split(",") if other_value else [], "choice_values": value.split(",") if value else []} if el_type == "ClassificationField" else None,
        "ChoiceField": {"other_values": other_value.split(",") if other_value else [], "choice_values": value.split(",") if value else []} if el_type == "ChoiceField" else None,
        "RecordLinkField": get_record_link(record_id, value) if el_type == "RecordLinkField" else None,
        "AddressField": {postfix: row[data_name + "_" + postfix] for postfix in ["sub_thoroughfare", "thoroughfare", "suite", "locality", "sub_admin_area", "admin_area", "postal_code", "country"]} if el_type == "AddressField" else None,
        "PhotoField": [{"photo_id": v, "caption": caption_value.split(",")[i]} for i, v in enumerate(value.split(","))] if value and caption_value else [] if el_type == "PhotoField" else None,
        "AudioField": [{"audio_id": v, "caption": caption_value.split(",")[i]} for i, v in enumerate(value.split(","))] if value and caption_value else [] if el_type == "AudioField" else None,
        "VideoField": [{"video_id": v, "caption": caption_value.split(",")[i]} for i, v in enumerate(value.split(","))] if value and caption_value else [] if el_type == "VideoField" else None,
        "Repeatable": read_repeatable_data(record_id, element) if el_type == "Repeatable" else None,
        "TextField": handle_text_field(value, element) if el_type == "TextField" else None,
        # TODO: Handle if we have any of these types
        "SignatureField": {"timestamp": "", "signature_id": ""} if el_type == "SignatureField" else None,
    }

    if el_type in object_types:
        return object_types[el_type]

    return value


def flatten(l):
    for el in l:
        if (el["type"] == "Section" or el["type"] == "Repeatable") and "elements" in el:
            yield el
            yield from flatten(el["elements"])
        else:
            yield el


def get_project_id(project_name):
    global PROJECT_IDS

    if not project_name:
        return None

    if project_name not in PROJECT_IDS:
        res = FULCRUM.projects.search(project_name)

        for project in res["projects"]:
            if project["name"] == project_name:
                PROJECT_IDS[project["name"]] = project["id"]
                break

        if project_name not in PROJECT_IDS:
            print("Could not find project with name: " + project_name)
            return None

    return PROJECT_IDS[project_name]


def get_user_id(email):
    global USER_IDS

    if not email:
        return None

    if email not in USER_IDS:
        res = FULCRUM.memberships.search()

        for membership in res["memberships"]:
            if membership["email"] == email:
                USER_IDS[email] = membership["user_id"]
                break

        if email not in USER_IDS:
            print("Could not find user with email: " + email)
            return None

    return USER_IDS[email]


def create_base_record(form_id, row, base_obj={}):
    latitude_val = row["latitude"]
    longitude_val = row["longitude"]

    try:
        latitude_val = float(latitude_val)
    except Exception:
        latitude_val = None

    try:
        longitude_val = float(longitude_val)
    except Exception:
        longitude_val = None

    return {
        "record": {
            **base_obj,
            "form_id": form_id,
            "latitude": latitude_val,
            "longitude": longitude_val,
            "project_id": get_project_id(row["project"]),
            "assigned_to_id": get_user_id(row["assigned_to"]),
            "client_created_at": convert_to_epoch(row["system_created_at"]),
            "client_updated_at": convert_to_epoch(row["system_updated_at"]),
            "fulcrum_id": row["fulcrum_id"],
            **({"fulcrum_parent_id_not_used": row["fulcrum_parent_id_not_used"]} if TYPE == "survey" else {}),
            "form_values": {}
        }
    }


def create_repeatable_objects(elements, rows, parent_id=None):
    repeatables_objects = []

    for row in rows:
        latitute_val = row["latitude"]
        longitude_val = row["longitude"]

        try:
            latitute_val = float(latitute_val)
        except Exception:
            latitute_val = None

        try:
            longitude_val = float(longitude_val)
        except Exception:
            longitude_val = None

        new_obj = {
            "latitude": latitute_val,
            "longitude": longitude_val,
            "form_values": {}
        }

        for element in elements:
            key = element["key"]

            value_obj = create_value_structure(
                element, row, record_id=parent_id)

            if value_obj is not None:
                new_obj["form_values"][key] = value_obj

        repeatables_objects.append(new_obj)

    return repeatables_objects


def create_records(form_id, elements, rows, base_obj={}):
    all_records = []

    for row in rows:
        new_record = create_base_record(form_id, row, base_obj)

        for element in elements:
            key = element["key"]
            record_id = row["fulcrum_id"]

            value_obj = create_value_structure(
                element, row, record_id)

            if value_obj is not None:
                new_record["record"]["form_values"][key] = value_obj

        # Delete any null values
        keys_to_delete = []

        for key, value in new_record["record"]["form_values"].items():
            if value is None or value == "":
                keys_to_delete.append(key)

            if isinstance(value, list):
                if len(value) == 0:
                    keys_to_delete.append(key)

            if isinstance(value, dict):
                if "choice_values" in value and "other_values" in value:
                    if len(value["choice_values"]) == 0 and len(value["other_values"]) == 0:
                        keys_to_delete.append(key)

        for key in keys_to_delete:
            del new_record["record"]["form_values"][key]

        all_records.append(new_record)

    return all_records


def main():
    if TYPE == "survey":
        # Remove the IMPORT_MAPPING_FILE file
        if os.path.exists(PARENT_TO_LATEST_SURVEY_ID):
            os.remove(PARENT_TO_LATEST_SURVEY_ID)

    target_form = None

    forms = FULCRUM.forms.search()

    for form in forms["forms"]:
        if form["name"] == FORM_NAME:
            target_form = form
            break

    if not target_form:
        print("Form not found")
        return

    form_id = target_form["id"]

    # Process:
    # 1. We transform the records into a list of data names instead of IDs
    #    - Match on "data_name" within target_form["elements"][i], get "key" property
    # 2. With "key" and "data_name" properties, create a { "{key}": "{data_name}" } mapping object
    # 3. With "key" and "data_name" properties, create a { "{data_name}": "{key}" } mapping object
    # 4. Create an object ({"{data_name}": obj }) for each value in the form, this object will depend on the target_form["elements"][i] properties
    # 5. With each object, we transform the data_name into a key using the mapping object

    flattened_elements = list(flatten(target_form["elements"]))
    # repeatables = get_repeatables(target_form["elements"])

    csv_base = os.path.join(SOURCE_DIR, "base.csv")

    data_name_key_mapping = {k["data_name"]: k["key"]
                             for k in flattened_elements}

    for value in data_name_key_mapping.values():
        # Check if the value occurs more than once in the values
        if list(data_name_key_mapping.values()).count(value) > 1:
            print("Duplicate key found: " + value)
            exit()

    rows = read_csv(csv_base)
    records = create_records(form_id, flattened_elements, rows)

    # save_records(records)
    # save_first_record(form_id)
    # save_form()
    # print(json.dumps(records, indent=2))
    print("Records to upload: " + str(len(records)))

    upload_records(records)


if TYPE != "survey" and TYPE != "site_visits":
    print("Invalid type: " + TYPE)
    exit()

if __name__ == '__main__':
    answer = input("Are you sure? (y/n): ")

    if answer == "y":
        main()
        print("Done.")
    else:
        print("Exiting...")
