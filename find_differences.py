# We want to open 2 csv files and read both files into 2 separate arrays
# For every column that is in both files, we mark as "found"
# For every column that is not in both files, we mark as "not found"

# We want to find the closest match of "not found" columns between the 2 arrays
# For every closest match, we ask the user if they would like to replace the column with the closest match
# If they respond with "y" then we make the replace and progressively save the updated csv file to a new location
# If they respond with "n" then we skip and check the next column
# If they respond with anything else, we take that value, assign it to the column and save the updated csv file to the new location

import argparse
import csv
import difflib
import json
import os
import re
import shutil

from tabulate import tabulate

# Arguments
parser = argparse.ArgumentParser(
    description="Find differences between 2 csv files")

parser.add_argument("--parent-dir", type=str,
                    help="Parent directory", required=True)
parser.add_argument("--base_dir", type=str,
                    help="Base directory", required=True)
parser.add_argument("--base_prefix", type=str,
                    help="Base prefix", required=True)
parser.add_argument("--target_dir", type=str,
                    help="Target directory", required=True)
parser.add_argument("--target_prefix", type=str,
                    help="Target prefix", required=True)

args = parser.parse_args()

# Constants

PARENT_DIR = args.parent_dir

BASE_PARENT_DIR = f"new_files\\{PARENT_DIR}"

BASE_DIR = args.base_dir
BASE_PREFIX = args.base_prefix

TARGET_DIR = args.target_dir
TARGET_PREFIX = args.target_prefix


# Functions

def read_csv_columns(file_path):
    """Read a csv file and return a list of rows"""
    # Open the file
    with open(file_path, "r") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames)


def create_table(rows):
    return [
        ["Column", "Closest Match", "Updated"],
        *rows
    ]


def delete_mismatch_file():
    if os.path.exists(f"{BASE_PARENT_DIR}\\repeatable_mismatches.txt"):
        os.remove(f"{BASE_PARENT_DIR}\\repeatable_mismatches.txt")


def write_file_no_match(filepath):
    with open(f"{BASE_PARENT_DIR}\\repeatable_mismatches.txt", "a") as f:
        f.write(filepath + "\n")


def custom_rules(row):
    new_val = row

    if PARENT_DIR == "KSMP":
        if re.match(r"^.*?_year_1$", row):
            new_val = re.sub(r"^(.*?)_year_1$", "\\1", row)
            print(f"Custom Rule. Replacing: '{row}' with '{new_val}'")
        elif re.match(r"^.*?_year_1_other$", row):
            new_val = re.sub(r"^(.*?)_year_1_other$", "\\1_other", row)
            print(f"Custom Rule. Replacing: '{row}' with '{new_val}'")
        elif re.match(r"^.*?(_schedule)?_year_.*$", row):
            new_val = re.sub(r"^(.*?)(_schedule)?_year_(.*)$", "\\1_\\3", row)
            print(f"Custom Rule. Replacing: '{row}' with '{new_val}'")
    elif PARENT_DIR == "JKMR":
        pass

    return new_val != row, new_val


def get_files(dir, prefix):
    return [f for f in os.listdir(dir) if os.path.isfile(
        os.path.join(dir, f)) and f.startswith(prefix) and f.endswith(".csv")]


def does_file_exist(filepath):
    return os.path.isfile(filepath)


def clear_and_create_dir(dir):
    if os.path.exists(dir):
        shutil.rmtree(dir)
    os.makedirs(dir)


def get_base_file(postfix=None):
    if PARENT_DIR == "JKMR":
        if postfix == "site_plans":
            postfix = "break_before_site_plans"
        elif postfix == "site_photo_property":
            postfix = "site_photos_property"
        elif postfix == "knotweed_survey_knotweed_stand_details":
            postfix = "knotweed_stand_details"
        elif postfix == "knotweed_survey_knotweed_stand_details_stand_photos":
            postfix = "knotweed_stand_details_stand_photos"

    return postfix, os.path.join(BASE_DIR, f"{BASE_PREFIX}{('_' + postfix) if postfix else ''}.csv")


def transform_knotweed_survey_repeatable_jkmr():
    # We want to take in a csv file for the knotweed survey repeatable
    # We then want to identify all parent records and read the data for that parent record ID into a dictionary
    # For each record within the survey record, we want to create a new record joined with the parent record data
    # We then want to take these new records and write them to a new csv file
    parent_record_ids = []
    parent_record_data = {}
    child_records_mapping = {}
    with open(os.path.join(TARGET_DIR, f"{TARGET_PREFIX}_knotweed_survey.csv"), "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

        # Get all parent records
        parent_record_ids = [r["fulcrum_parent_id"] for r in rows]

        for r in rows:
            if r["fulcrum_parent_id"] not in child_records_mapping.keys():
                child_records_mapping[r["fulcrum_parent_id"]] = [r]
            else:
                child_records_mapping[r["fulcrum_parent_id"]].append(r)

    # Get all the data for each parent record

    with open(os.path.join(TARGET_DIR, f"{TARGET_PREFIX}.csv")) as f:
        reader = csv.DictReader(f)
        rows = list(reader)

        # Get the data for each parent record
        for r in rows:
            if r["fulcrum_id"] in parent_record_data.keys():
                # We have already seen this record
                continue

            if r["fulcrum_id"] in parent_record_ids:
                # This is a parent record, grab the data
                parent_record_data[r["fulcrum_id"]] = r

    # Join the data together
    new_rows = []
    for parent_id, child_records in child_records_mapping.items():
        for child_record in child_records:
            child_keys = ["child_" + k for k in child_record.keys()]
            new_row = {"fulcrum_id": child_record["fulcrum_id"],
                       **{k: parent_record_data[parent_id][k] for k in parent_record_data[parent_id].keys() if k != "fulcrum_id"},
                       **{k: child_record[re.sub(r"^child_", "", k)] for k in child_keys if k != "child_fulcrum_id"}}
            new_rows.append(new_row)

    # Write the new data to a new csv file
    with open(os.path.join(TARGET_DIR, f"{TARGET_PREFIX}_base_re_written.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=new_rows[0].keys())
        writer.writeheader()
        writer.writerows(new_rows)


def find_and_write_diffs(base, target, prefix):
    # Find differences
    diff = [f for f in target if f not in base]

    # Find matches
    # matches = [f for f in target if f in base]

    # Find unmatched
    unmatched = [f for f in base if f not in target]

    # Find closest matches
    closest_matches = [difflib.get_close_matches(
        f, unmatched, n=1, cutoff=0) for f in diff]

    rows = list(zip(diff, ["N/A" if not f else f[0]
                           for f in closest_matches], ["" for f in closest_matches]))

    # Create table
    table = create_table(rows)

    # Print table
    print(tabulate(table, headers="firstrow", tablefmt="fancy_grid"))

    # Print empty line
    print()

    dest_dir = f"{BASE_PARENT_DIR}\\differences\\{prefix}"
    clear_and_create_dir(dest_dir)

    diff_file_dest = f"{dest_dir}\\differences.csv"

    # Save table to file
    with open(diff_file_dest, "w", newline="") as f:
        csv.writer(f).writerows(table)

    # Read mappings from file
    mappings = {}
    mappings_exist = False

    mappings_dir = f"{BASE_PARENT_DIR}\\mappings\\{prefix}"

    if not os.path.exists(mappings_dir):
        os.makedirs(mappings_dir)

    mappings_file = f"{mappings_dir}\\mappings.json"

    if os.path.exists(mappings_file):
        with open(mappings_file, "r") as f:
            mappings = json.load(f)
            mappings_exist = True

    for i, row in enumerate(rows):
        # Save table to file
        with open(diff_file_dest, "w", newline="") as f:
            csv.writer(f).writerows(create_table(rows))

        if row[1] != "N/A":
            # Check if mapping exists
            if row[0] in mappings:
                print(f"Replacing: '{row[0]}' with '{mappings[row[0]]}'")
                rows[i] = [row[0], row[1], mappings[row[0]]]
                if (mappings[row[0]] in unmatched):
                    unmatched.remove(mappings[row[0]])
                continue
            elif mappings_exist:
                print(f"Skipping: '{row[0]}'")
                continue

            changed, new_val = custom_rules(row[0])

            if changed:
                rows[i] = [row[0], row[1], new_val]
                if (new_val in unmatched):
                    unmatched.remove(new_val)
                mappings[row[0]] = new_val
            else:
                print(
                    f"Replace:\n{row[0]}\n{row[1]}? (y/n/type your own column name)")
                response = input()
                response = response.lower().strip()

                if response == "y" or response == "":
                    # Replace column
                    print(f"Replacing: '{row[0]}' with '{row[1]}'")
                    rows[i] = [row[0], row[1], row[1]]
                    if (row[1] in unmatched):
                        unmatched.remove(row[1])
                    mappings[row[0]] = row[1]
                elif response == "n":
                    print(f"Skipping: '{row[0]}'")
                    continue
                else:
                    if (response not in unmatched):
                        print(f"Invalid column: '{response}'")
                        continue
                    print(f"Replacing: '{row[0]}' with '{response}'")
                    rows[i] = [row[0], row[1], response]
                    if (response in unmatched):
                        unmatched.remove(response)
                    mappings[row[0]] = response
        else:
            print(f"No match found for '{row[0]}'")
        print()

    # Final write
    with open(diff_file_dest, "w", newline="") as f:
        csv.writer(f).writerows(create_table(rows))

    # Write mappings to file
    with open(mappings_file, "w") as f:
        json.dump(mappings, f, indent=2)

    unmatched_file_dest = f"{dest_dir}\\unmatched_columns.csv"

    # Write unmatched columns to file
    with open(unmatched_file_dest, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Missing Columns"])
        writer.writerows([[f] for f in unmatched])


# Main

if not os.path.exists(f"{BASE_PARENT_DIR}"):
    os.makedirs(f"{BASE_PARENT_DIR}")

delete_mismatch_file()

if PARENT_DIR == "JKMR":
    transform_knotweed_survey_repeatable_jkmr()

# Read all the files in the base & target directory
base_files = get_files(BASE_DIR, BASE_PREFIX)
target_files = get_files(TARGET_DIR, TARGET_PREFIX)

for f in target_files:
    if f == f"{TARGET_PREFIX}_base_re_written.csv" or f == f"{TARGET_PREFIX}_knotweed_survey.csv":
        # Skip this re-written file
        continue

    # If the file is the prefix then this is the parent file
    if f == f"{TARGET_PREFIX}.csv":
        new_postfix, base_filepath = get_base_file()

        does_base_file_exist = does_file_exist(base_filepath)

        # If the base file doesn't exist then raise an exception
        if not does_base_file_exist:
            write_file_no_match(base_filepath)

        # Read the files
        base_rows = read_csv_columns(
            base_filepath
        ) if does_base_file_exist else []
        target_rows = read_csv_columns(os.path.join(
            TARGET_DIR, f if PARENT_DIR != "JKMR" else f"{TARGET_PREFIX}_base_re_written.csv"))

        # Find and write differences
        find_and_write_diffs(base_rows, target_rows,
                             "base" if does_base_file_exist else "NO_MATCH_base")
    else:
        # These are the child repeatables
        # Grab the postfix
        postfix = f.replace(f"{TARGET_PREFIX}_", "").replace(".csv", "")

        # Base filepath
        new_postfix, base_filepath = get_base_file(postfix)

        does_base_file_exist = does_file_exist(base_filepath)

        # If the base file doesn't exist then raise an exception
        if not does_base_file_exist:
            write_file_no_match(base_filepath)

        # Read the files
        base_rows = read_csv_columns(
            base_filepath
        ) if does_base_file_exist else []
        target_rows = read_csv_columns(os.path.join(TARGET_DIR, f))

        # Find and write differences
        find_and_write_diffs(base_rows, target_rows, new_postfix.lower(
        ) if does_base_file_exist else "NO_MATCH_" + new_postfix.lower())
