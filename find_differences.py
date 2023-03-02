# We want to open 2 csv files and read both files into 2 separate arrays
# For every column that is in both files, we mark as "found"
# For every column that is not in both files, we mark as "not found"

# We want to find the closest match of "not found" columns between the 2 arrays
# For every closest match, we ask the user if they would like to replace the column with the closest match
# If they respond with "y" then we make the replace and progressively save the updated csv file to a new location
# If they respond with "n" then we skip and check the next column
# If they respond with anything else, we take that value, assign it to the column and save the updated csv file to the new location

import csv
import difflib
import json
import os
import re

from tabulate import tabulate

MAPPINGS_FILE = "new_files\\mappings.json"

if not os.path.exists("new_files"):
    os.makedirs("new_files")


def read_csv_columns(file_path):
    """Read a csv file and return a list of rows"""
    # Open the file
    cols = []
    with open(file_path, "r") as f:
        reader = csv.DictReader(f)
        for line in reader:
            cols = line.keys()
            return cols


def create_table(rows):
    return [
        ["Column", "Closest Match", "Updated"],
        *rows
    ]


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


base = read_csv_columns(
    "export survey app - 1 record\\bb_survey_app_do_not_use\\bb_survey_app_do_not_use.csv")
array_2 = read_csv_columns(
    "knotweed_survey_and_management_plan\\knotweed_survey_and_management_plan.csv")

# Find differences
diff = [f for f in array_2 if f not in base]

# Find matches
matches = [f for f in array_2 if f in base]

# Find unmatched
unmatched = [f for f in base if f not in array_2]

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

# Save table to file
with open("new_files\\differences.csv", "w") as f:
    csv.writer(f).writerows(table)

# Read mappings from file
mappings = {}
mappingsExist = False

if os.path.exists(MAPPINGS_FILE):
    with open(MAPPINGS_FILE, "r") as f:
        mappings = json.load(f)
        mappingsExist = True

for i, row in enumerate(rows):
    # Save table to file
    with open("new_files\\differences.csv", "w") as f:
        csv.writer(f).writerows(create_table(rows))

    if row[1] != "N/A":
        # Check if mapping exists
        if row[0] in mappings:
            print(f"Replacing: '{row[0]}' with '{mappings[row[0]]}'")
            rows[i] = [row[0], row[1], mappings[row[0]]]
            if (mappings[row[0]] in unmatched):
                unmatched.remove(mappings[row[0]])
            continue
        elif mappingsExist:
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

# Write mappings to file
with open(MAPPINGS_FILE, "w") as f:
    json.dump(mappings, f, indent=2)

# Write unmatched columns to file
with open("new_files\\unmatched_columns.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Missing Columns"])
    writer.writerows([[f] for f in unmatched])
