import csv
import os
import re

if not os.path.exists("new_files"):
    os.makedirs("new_files")


def read_csv(file_path):
    """Read a csv file and return a list of rows"""
    with open(file_path, "r") as f:

        reader = csv.DictReader(f)
        return list(reader)


diff = read_csv("new_files\\differences.csv")
cols = [f["Column"] for f in diff]

data = read_csv(
    "knotweed_survey_and_management_plan\\knotweed_survey_and_management_plan.csv")

unmatched_columns = [f["Missing Columns"]
                     for f in read_csv("new_files\\unmatched_columns.csv")]

print(cols)

new_cols = list(data[0].keys())

site_location_csv = read_csv(
    "bb_site_location_import\\bb_site_location_import.csv")

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

property_type_mappings = {
    "Private Residential": "Residential",
    "Housing Association": "Developer",
    "Commercial": "Commercial",
    "Council": "Residential",
    "Education": "Commercial",
    "Healthcare": "Commercial",
    "Industrial": "Commercial",
}

additional_cols = {
    "record_type": lambda row: "Management Plan",
    "client_type": lambda row: property_type_mappings[[k for k in property_type_mappings.keys() if re.match(k, row["property_type"])][0]] if any([re.match(k, row["property_type"]) for k in property_type_mappings.keys()]) else "",
    "plant_type": lambda row: "Japanese Knotweed",
    "job_type": lambda row: "Treatment",
}

# Set every row "record_type" column to "Management Plan"
for i, row in enumerate(data):
    # for col in unmatched_columns:
    #     if col not in data[i].keys():
    #         data[i][col] = ""

    for (col, func) in additional_cols.items():
        data[i][col] = func(row)

# print(data[0].keys())

with open("new_files\\NEW_RECORDS.csv", "w", newline="") as f:
    writer = csv.writer(f, strict=True)
    writer.writerow(
        [*new_cols, "site_location", *additional_cols.keys()])

    rows = [list(f.values()) for f in data]
    writer.writerows(rows)
