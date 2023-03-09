import argparse
import csv
import os
import re
import shutil

# Arguments
parser = argparse.ArgumentParser(
    description="Find differences between 2 csv files")

parser.add_argument("--parent-dir", type=str,
                    help="Parent directory", required=True)
parser.add_argument("--target_dir", type=str,
                    help="Target directory", required=True)
parser.add_argument("--target_prefix", type=str,
                    help="Target prefix", required=True)
parser.add_argument("--site_location_file", type=str,
                    help="Site location file", required=True)
parser.add_argument("--client_name_col", type=str,
                    help="Client name column", required=True)
parser.add_argument("--acc_ref_col", type=str,
                    help="Account reference column", required=True)

args = parser.parse_args()


# Constants

PARENT_DIR = args.parent_dir
BASE_PARENT_DIR = f"new_files\\{PARENT_DIR}"

TARGET_DIR = args.target_dir
TARGET_PREFIX = args.target_prefix

CLIENT_NAME_COL = args.client_name_col
ACC_REF_COL = args.acc_ref_col

SITE_LOCATION_FILE = args.site_location_file

TRANSFORMATIONS = {
    "KSMP": {
        "base": {
            "property_type":
                {
                    "Private Residential": "Residential",
                    "Housing Association": "Developer",
                    "Commercial": "Commercial",
                    "Council": "Residential",
                    "Education": "Commercial",
                    "Healthcare": "Commercial",
                    "Industrial": "Commercial",
                },
        }
    },
    "JKMR": {
        "base": {
            "property_type": {
                "Private Residential": "Residential",
                "Housing Association": "Developer",
                "Commercial": "Commercial",
                "Council": "Residential",
                "Education": "Commercial",
                "Healthcare": "Commercial",
                "Industrial": "Commercial",
            }
        },
        "stand_details": {
            "stand_location": {
                "Within client property only": "Site only",
                "Within client property and one other property": "Site and one adjacent property",
                "Within client property and more than one other property": "Site and more than one other property",
                "Within an adjacent property only": "One adjacent property only",
                "Within more than one adjacent property": "More than one other property only",
            }
        }
    }
}


# Functions

def read_csv(file_path):
    """Read a csv file and return a list of rows"""
    with open(file_path, "r") as f:

        reader = csv.DictReader(f)
        return list(reader)


def get_files(dir):
    return [f for f in os.listdir(dir) if os.path.isfile(
        os.path.join(dir, f)) and f.endswith(".csv")]


def get_dirs(dir):
    return [f for f in os.listdir(dir) if os.path.isdir(
        os.path.join(dir, f))]


def does_file_exist(filepath):
    return os.path.isfile(filepath)


def clear_and_create_dir(dir):
    if os.path.exists(dir):
        shutil.rmtree(dir)
    os.makedirs(dir)


def transform(diff_dir_name, target_csv_name):
    diff = read_csv(
        f"{BASE_PARENT_DIR}\\differences\\{diff_dir_name}\\differences.csv")
    cols = [f["Column"] for f in diff]

    data = read_csv(f"{TARGET_DIR}\\{TARGET_PREFIX}_{target_csv_name}.csv" if target_csv_name !=
                    "base" else f"{TARGET_DIR}\\{TARGET_PREFIX}.csv")

    new_cols = list(data[0].keys())

    site_location_csv = read_csv(SITE_LOCATION_FILE)

    # Update columns
    for i, orig_col in enumerate(new_cols):
        if (orig_col not in cols):
            print(f"Skipping {orig_col}")
            continue

        found_i = cols.index(orig_col)
        val = diff[found_i]["Updated"].strip()

        if (val == "" or val == "N/A"):
            continue

        print(f"Replacing {new_cols[i]} with {val}")
        new_cols[i] = val

    site_address_checks = ["site_address_postal_code", "site_address_thoroughfare",
                           "site_address_sub_thoroughfare", "site_address_locality", "site_address_admin_area", "site_address_country"]

    # Match on site full address, client name and job id write this to the end file for the "site_location" link
    if target_csv_name == "base":
        for i, row in enumerate(data):
            found = False

            for site_location in site_location_csv:
                match = False

                for check in site_address_checks:
                    if (row[check] != site_location[check]):
                        match = False
                        break
                    else:
                        match = True

                if (match and row[CLIENT_NAME_COL].strip() == site_location["client_name"] and row[ACC_REF_COL] == site_location["job_id"]):
                    data[i]["site_location"] = site_location["fulcrum_id"]
                    found = True
                    break

            if (not found):
                raise Exception(
                    f"Could not find site location: {data[i]['fulcrum_id']}")

    property_type_mappings = {
        "Private Residential": "Residential",
        "Housing Association": "Developer",
        "Commercial": "Commercial",
        "Council": "Residential",
        "Education": "Commercial",
        "Healthcare": "Commercial",
        "Industrial": "Commercial",
    }

    default_base_cols = {
        "record_type": lambda row: "Management Plan",
        "client_type": lambda row: property_type_mappings[[k for k in property_type_mappings.keys() if re.match(k, row["property_type"])][0]] if any([re.match(k, row["property_type"]) for k in property_type_mappings.keys()]) else "",
        "plant_type": lambda row: "Japanese Knotweed",
        "job_type": lambda row: "Treatment",
        "document_version": lambda row: "1.0",
    }

    # Set every row "record_type" column to "Management Plan"
    for i, row in enumerate(data):
        if (diff_dir_name == "base"):
            for (col, func) in default_base_cols.items():
                data[i][col] = func(row)

    with open(f"{BASE_PARENT_DIR}\\new_records\\{diff_dir_name}.csv", "w", newline="") as f:
        writer = csv.writer(f, strict=True)
        writer.writerow(
            [*new_cols, "site_location", *(list(filter(lambda x: x not in new_cols, list(default_base_cols.keys()))) if diff_dir_name == "base" else [])])

        rows = [list(f.values()) for f in data]
        writer.writerows(rows)


def get_file_mapping(dir_name):
    if PARENT_DIR == "JKMR":
        if dir_name == "break_before_site_plans":
            dir_name = "site_plans"
        elif dir_name == "site_photos_property":
            dir_name = "site_photo_property"
        elif dir_name == "knotweed_stand_details":
            dir_name = "knotweed_survey_knotweed_stand_details"
        elif dir_name == "knotweed_stand_details_stand_photos":
            dir_name = "knotweed_survey_knotweed_stand_details_stand_photos"

    return dir_name

# Main


clear_and_create_dir(f"{BASE_PARENT_DIR}\\new_records")

for dir in get_dirs(f"{BASE_PARENT_DIR}\\differences"):
    if dir.startswith("NO_MATCH_"):
        continue
    mapped_file = get_file_mapping(dir)
    transform(dir, mapped_file)
