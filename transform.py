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

args = parser.parse_args()


# Constants

PARENT_DIR = args.parent_dir

BASE_PARENT_DIR = f"new_files\\{PARENT_DIR}"

TARGET_DIR = args.target_dir
TARGET_PREFIX = args.target_prefix

SITE_LOCATION_FILE = args.site_location_file

MAPPINGS = {
    "KSMP": {
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


def transform(repeatable_name):
    diff = read_csv(f"{BASE_PARENT_DIR}\\differences\\{repeatable_name}\\differences.csv")
    cols = [f["Column"] for f in diff]

    print(diff)

    data = read_csv(f"{TARGET_DIR}\\{TARGET_PREFIX}_{repeatable_name}.csv" if repeatable_name !=
                    "base" else f"{TARGET_DIR}\\{TARGET_PREFIX}.csv")

    print(cols)

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

            if (match and row["client_name"] == site_location["client_name"] and row["account_reference"] == site_location["job_id"]):
                data[i]["site_location"] = site_location["fulcrum_id"]
                found = True
                break

        if (not found):
            raise Exception(
                f"Could not find site location: {data[i]['fulcrum_id']}")

    default_cols = {
        "record_type": lambda row: "Management Plan",
        "client_type": lambda row: MAPPINGS[PARENT_DIR]["base"]["property_type"][row["property_type"]],
        "plant_type": lambda row: "Japanese Knotweed",
        "job_type": lambda row: "Treatment",
        "document_version": lambda row: "1.0",
    }

    # Set every row "record_type" column to "Management Plan"
    for i, row in enumerate(data):
        for (col, func) in default_cols.items():
            data[i][col] = func(row)

    with open(f"{BASE_PARENT_DIR}\\new_records\\{repeatable_name}.csv", "w", newline="") as f:
        writer = csv.writer(f, strict=True)
        writer.writerow(
            [*new_cols, "site_location", *list(filter(lambda x: x not in new_cols, list(default_cols.keys())))])

        rows = [list(f.values()) for f in data]
        writer.writerows(rows)

# Main


clear_and_create_dir(f"{BASE_PARENT_DIR}\\new_records")

for dir in get_dirs(f"{BASE_PARENT_DIR}\\differences"):
    transform(dir)