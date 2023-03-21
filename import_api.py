import argparse
import csv
import json
import os

from dotenv import load_dotenv
from fulcrum import Fulcrum

load_dotenv()

parser = argparse.ArgumentParser(
    description='Import data from a CSV file into Fulcrum.')
parser.add_argument(
    '--form_name', "-n", help='The name of the form to import data into.')
parser.add_argument(
    '--source_dir', "-s", help='The directory containing the CSV files to import.')

args = parser.parse_args()


# Constants

FORM_NAME = args.form_name
SOURCE_DIR = args.source_dir
FULCRUM_API_KEY = os.getenv('FULCRUM_API_KEY')

FULCRUM = Fulcrum(FULCRUM_API_KEY)

READ_REPEATABLES = {}

# Util


def save_first_record(form_id):
    records = FULCRUM.records.search(url_params={
        'form_id': form_id})['records']

    with open("record.json", "w") as f:
        json.dump(records[0], f, indent=2)


def save_form(target_form):
    with open("form.json", "w") as f:
        json.dump(target_form, f, indent=2)


# Main

def read_csv(file_path):
    """Read a csv file and return a list of rows"""
    with open(file_path, "r") as f:
        reader = csv.DictReader(f)
        return list(reader)


def get_csv_files(dir):
    return [f for f in os.listdir(dir) if os.path.isfile(
        os.path.join(dir, f)) and f.endswith(".csv")]


def upload_records(records):
    for record in records:
        res = FULCRUM.records.create(record)
        print(res['record']['id'] + ' created.')


def read_repeatable_data(element):
    global READ_REPEATABLES

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

    return create_repeatable_objects(flattened_elements, rows)


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


def create_value_structure(element, row):
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
        "RecordLinkField": [{"record_id": v} for v in (value.split(",") if value else [None])] if el_type == "RecordLinkField" else None,
        "AddressField": {postfix: row[data_name + "_" + postfix] for postfix in ["sub_thoroughfare", "thoroughfare", "suite", "locality", "sub_admin_area", "admin_area", "postal_code", "country"]} if el_type == "AddressField" else None,
        "PhotoField": [{"photo_id": v, "caption": caption_value.split(",")[i]} for i, v in enumerate(value.split(","))] if value and caption_value else [] if el_type == "PhotoField" else None,
        "AudioField": [{"audio_id": v, "caption": caption_value.split(",")[i]} for i, v in enumerate(value.split(","))] if value and caption_value else [] if el_type == "AudioField" else None,
        "VideoField": [{"video_id": v, "caption": caption_value.split(",")[i]} for i, v in enumerate(value.split(","))] if value and caption_value else [] if el_type == "VideoField" else None,
        "Repeatable": read_repeatable_data(element) if el_type == "Repeatable" else None,
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


def create_base_record(form_id, row):
    return {
        "record": {
            "form_id": form_id,
            "latitude": float(row["latitude"]),
            "longitude": float(row["longitude"]),
            "form_values": {}
        }
    }


def create_repeatable_objects(elements, rows):
    repeatables_objects = []

    for row in rows:
        new_obj = {
            "latitude": float(row["latitude"]),
            "longitude": float(row["longitude"]),
            "form_values": {}
        }

        for element in elements:
            key = element["key"]

            value_obj = create_value_structure(
                element, row)

            if value_obj is not None:
                new_obj["form_values"][key] = value_obj

        repeatables_objects.append(new_obj)

    return repeatables_objects


def create_records(form_id, elements, rows):
    all_records = []

    for row in rows:
        new_record = create_base_record(form_id, row)

        for element in elements:
            key = element["key"]

            value_obj = create_value_structure(
                element, row)

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
    forms = FULCRUM.forms.search(FORM_NAME)

    for form in forms["forms"]:
        if form["name"] == FORM_NAME:
            target_form = form
            break

    if target_form is None:
        print("Form not found.")
        exit()

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

    with open("all_records.json", "w") as f:
        json.dump(records, f, indent=2)

    # save_first_record()
    # save_form()
    # print(json.dumps(records, indent=2))

    upload_records(records)


if __name__ == '__main__':
    answer = input("Are you sure? (y/n): ")

    if answer == "y":
        main()
        print("Done.")
    else:
        print("Exiting...")
