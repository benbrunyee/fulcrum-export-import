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


def upload_records(obj):
    record = FULCRUM.records.create(obj)
    print(record)
    print(record['record']['id'] + ' created.')


def create_value_structure(element, value):
    obj = None
    el_type = element["type"]

    skip_types = [
        "Section"
    ]

    object_types = {
        "ClassificationField": {"other_values": [], "choice_values": [value]},
        "ChoiceField": {"other_values": [], "choice_values": [value]},
        "RecordLinkField": [{"record_id": v} for v in value.split(",")],
        "AddressField": {"sub_thoroughfare": "", "thoroughfare": "", "suite": "", "locality": "", "sub_admin_area": "", "admin_area": "", "postal_code": "", "country": ""},
        "PhotoField": [{"photo_id": v, "caption": ""} for v in value.split(",")],
        "AudioField": [{"audio_id": v, "caption": ""} for v in value.split(",")],
        "VideoField": [{"video_id": v, "caption": ""} for v in value.split(",")],
        "SignatureField": {"timestamp": "", "signature_id": ""},
        "Repeatable": {"id": "", "geometry": {"type": "Point", "coordinates": []}, "form_values": {}},
    }

    if el_type in skip_types:
        return None

    if el_type in object_types.keys():
        obj = object_types[el_type]
        return obj

    return value


def isCaptionField(el_type):
    if el_type == "PhotoField" or el_type == "AudioField" or el_type == "VideoField":
        return True
    return False


def flatten(l):
    for el in l:
        if el["type"] == "Section" and "elements" in el:
            yield el
            yield from flatten(el["elements"])
        else:
            yield el


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

    new_records = {
        "record": {
            "form_id": target_form_id,
            "latitude": 0,
            "longitude": 0,
            "form_values": {}
        }
    }

    flattened_elements = list(flatten(target_form["elements"]))

    csv_files = get_csv_files(SOURCE_DIR)

    data_name_key_mapping = {k["data_name"]: k["key"]
                             for k in flattened_elements}

    for value in data_name_key_mapping.values():
        # Check if the value occurs more than once in the values
        if list(data_name_key_mapping.values()).count(value) > 1:
            print("Duplicate key found: " + value)
            exit()

    for csv in csv_files:
        csv_content = read_csv(os.path.join(SOURCE_DIR, csv))

        for row in csv_content:
            for key, value in row.items():
                for element in flattened_elements:
                    if element["data_name"] == key:
                        new_records["record"]["form_values"][element["key"]] = create_value_structure(
                            element, value)

                        if (isCaptionField(element["type"])):
                            media_caption_el = row[key + "_caption"] if key + \
                                "_caption" in row else None

                            if media_caption_el is None:
                                continue

                            captions = media_caption_el.split(",")
                            for i, entry in enumerate(new_records["record"]["form_values"][element["key"]]):
                                entry["caption"] = captions[i] if len(
                                    captions) > i else ""
        break

    with open("new_records.json", "w") as f:
        json.dump(new_records, f, indent=2)

    # save_first_record()
    # save_form()
    upload_records(new_records)


if __name__ == '__main__':
    answer = input("Are you sure? (y/n): ")

    if answer == "y":
        main()
