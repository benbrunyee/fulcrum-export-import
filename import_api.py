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

target_form = None
target_form_id = None


# Util

def save_first_record():
    records = FULCRUM.records.search(url_params={
        'form_id': target_form_id})['records']

    with open("record.json", "w") as f:
        json.dump(records[0], f, indent=2)


def save_form():
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
        print(res)
        print(res['record']['id'] + ' created.')


def create_value_structure(element, row):
    el_type = element["type"]
    data_name = element["data_name"]
    value = row[data_name] if data_name in row else None
    other_value = row[data_name +
                      "_other"] if data_name + "_other" in row else None
    caption_value = row[data_name +
                        "_caption"] if data_name + "_caption" in row else None

    skip_types = [
        "Section",
        "Repeatable",
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
        # TODO: Handle if we have any of these types
        "SignatureField": {"timestamp": "", "signature_id": ""} if el_type == "SignatureField" else None,
    }

    if el_type in object_types:
        return object_types[el_type]

    return value


def flatten(l):
    for el in l:
        if el["type"] == "Section" and "elements" in el:
            yield el
            yield from flatten(el["elements"])
        else:
            yield el


def create_base_record():
    return {
        "record": {
            "form_id": target_form_id,
            "latitude": 0,
            "longitude": 0,
            "form_values": {}
        }
    }


def create_records(elements, filepath):
    csv_content = read_csv(os.path.join(SOURCE_DIR, filepath))

    all_records = []
    new_record = create_base_record()

    for row in csv_content:
        for element in elements:
            data_name = element["data_name"]
            key = element["key"]

            value = row[data_name
                        ] if data_name in row else None

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
        new_record = create_base_record()

    return all_records


def main():
    global target_form
    global target_form_id

    forms = FULCRUM.forms.search(FORM_NAME)

    for form in forms["forms"]:
        if form["name"] == FORM_NAME:
            target_form = form
            break

    if target_form is None:
        print("Form not found.")
        exit()

    target_form_id = target_form["id"]

    # Process:
    # 1. We transform the records into a list of data names instead of IDs
    #    - Match on "data_name" within target_form["elements"][i], get "key" property
    # 2. With "key" and "data_name" properties, create a { "{key}": "{data_name}" } mapping object
    # 3. With "key" and "data_name" properties, create a { "{data_name}": "{key}" } mapping object
    # 4. Create an object ({"{data_name}": obj }) for each value in the form, this object will depend on the target_form["elements"][i] properties
    # 5. With each object, we transform the data_name into a key using the mapping object

    complete_records = []

    flattened_elements = list(flatten(target_form["elements"]))

    csv_files = get_csv_files(SOURCE_DIR)

    data_name_key_mapping = {k["data_name"]: k["key"]
                             for k in flattened_elements}

    for value in data_name_key_mapping.values():
        # Check if the value occurs more than once in the values
        if list(data_name_key_mapping.values()).count(value) > 1:
            print("Duplicate key found: " + value)
            exit()

    for csv_file in csv_files:
        isBase = csv_file == "base.csv"
        records = create_records(flattened_elements, csv_file)

        if isBase:
            complete_records.append(records)
            break

    with open("all_records.json", "w") as f:
        json.dump(complete_records, f, indent=2)

    # save_first_record()
    # save_form()
    upload_records(complete_records[0])


if __name__ == '__main__':
    answer = input("Are you sure? (y/n): ")

    if answer == "y":
        main()
        print("Done.")
    else:
        print("Exiting...")
