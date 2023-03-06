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

    if (re.match(r"^.*?_year_1$", row)):
        new_val = re.sub(r"^(.*?)_year_1$", "\\1", row)
        print(f"Custom Rule. Replacing: '{row}' with '{new_val}'")
    elif (re.match(r"^.*?_year_1_other$", row)):
        new_val = re.sub(r"^(.*?)_year_1_other$", "\\1_other", row)
        print(f"Custom Rule. Replacing: '{row}' with '{new_val}'")
    elif (re.match(r"^.*?(_schedule)?_year_.*$", row)):
        new_val = re.sub(r"^(.*?)(_schedule)?_year_(.*)$", "\\1_\\3", row)
        print(f"Custom Rule. Replacing: '{row}' with '{new_val}'")

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
    with open(diff_file_dest, "w") as f:
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
        with open(diff_file_dest, "w") as f:
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
    with open(diff_file_dest, "w") as f:
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

# Read all the files in the base & target directory
base_files = get_files(BASE_DIR, BASE_PREFIX)
target_files = get_files(TARGET_DIR, TARGET_PREFIX)

for f in target_files:

    # If the file is the prefix then this is the parent file
    if f == f"{TARGET_PREFIX}.csv":
        base_filepath = os.path.join(BASE_DIR, f"{BASE_PREFIX}.csv")

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
        find_and_write_diffs(base_rows, target_rows, "BASE")
    else:
        # These are the child repeatables
        # Grab the postfix
        postfix = f.replace(f"{TARGET_PREFIX}_", "").replace(".csv", "")

        # Base filepath
        base_filepath = os.path.join(BASE_DIR, f"{BASE_PREFIX}_{postfix}.csv")

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
        find_and_write_diffs(base_rows, target_rows, postfix.upper())
