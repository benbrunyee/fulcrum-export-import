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
import logging
import os
import re
import shutil

# Arguments
parser = argparse.ArgumentParser(description="Find differences between 2 csv files")

parser.add_argument(
    "--debug", action="store_true", help="Enable debug logging", required=False
)
parser.add_argument("--parent_dir", type=str, help="Parent directory", required=True)
parser.add_argument("--base_dir", type=str, help="Base directory", required=True)
parser.add_argument("--base_prefix", type=str, help="Base prefix", required=True)
parser.add_argument("--target_dir", type=str, help="Target directory", required=True)
parser.add_argument("--target_prefix", type=str, help="Target prefix", required=True)
parser.add_argument(
    "--skip_prompt_matching",
    action="store_true",
    help="Skip all prompt matching. Don't ask for user input.",
    required=False,
)

args = parser.parse_args()

# Logging

# Logging format of: [LEVEL]::[FUNCTION]::[HH:MM:SS] - [MESSAGE]
# Where the level is colored based on the level and the rest except from the message is grey
start = "\033["
end = "\033[0m"
colors = {
    "GREEN": "32m",
    "ORANGE": "33m",
    "RED": "31m",
    "GREY": "90m",
}
for color in colors:
    # Add the start to the color
    colors[color] = start + colors[color]

logging.addLevelName(logging.DEBUG, f"{colors['GREEN']}DEBUG{colors['GREY']}")  # Green
logging.addLevelName(logging.INFO, f"{colors['GREEN']}INFO{colors['GREY']}")  # Green
logging.addLevelName(
    logging.WARNING, f"{colors['ORANGE']}WARNING{colors['GREY']}"
)  # Orange
logging.addLevelName(logging.ERROR, f"{colors['RED']}ERROR{colors['GREY']}")  # Red
logging.addLevelName(
    logging.CRITICAL, f"{colors['RED']}CRITICAL{colors['GREY']}"
)  # Red

# Define the format of the logging
logging.basicConfig(
    format=f"%(levelname)s::%(funcName)s::%(asctime)s - {end}%(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG if args.debug else logging.INFO)


# Constants


PARENT_DIR = args.parent_dir

BASE_PARENT_DIR = f"new_files\\{PARENT_DIR}"

BASE_DIR = args.base_dir
BASE_PREFIX = args.base_prefix

TARGET_DIR = args.target_dir
TARGET_PREFIX = args.target_prefix

SKIP_PROMPT_MATCHING = args.skip_prompt_matching


# Functions


def read_csv_columns(file_path):
    """Read a csv file and return a list of rows"""
    # Open the file
    with open(file_path, "r") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames)


def create_table(rows):
    return [["Column", "Closest Match", "Updated"], *rows]


def delete_mismatch_file():
    if os.path.exists(f"{BASE_PARENT_DIR}\\repeatable_mismatches.txt"):
        os.remove(f"{BASE_PARENT_DIR}\\repeatable_mismatches.txt")


def write_file_no_match(filepath):
    with open(f"{BASE_PARENT_DIR}\\repeatable_mismatches.txt", "a") as f:
        f.write(filepath + "\n")


def apply_custom_rules(target_row):
    """
    Apply custom rules to the target row (input csv rows)
    """
    new_val = target_row

    if PARENT_DIR == "KSMP":
        if re.match(r"^.*?_year_1$", target_row):
            new_val = re.sub(r"^(.*?)_year_1$", "\\1", target_row)
            logger.debug(f"Custom Rule. Replacing: '{target_row}' with '{new_val}'")
        elif re.match(r"^.*?_year_1_other$", target_row):
            new_val = re.sub(r"^(.*?)_year_1_other$", "\\1_other", target_row)
            logger.debug(f"Custom Rule. Replacing: '{target_row}' with '{new_val}'")
        elif re.match(r"^.*?(_schedule)?_year_.*$", target_row):
            new_val = re.sub(r"^(.*?)(_schedule)?_year_(.*)$", "\\1_\\3", target_row)
            logger.debug(f"Custom Rule. Replacing: '{target_row}' with '{new_val}'")
    elif PARENT_DIR == "IPMR":
        if re.match(r"^.*?_year_1$", target_row):
            new_val = re.sub(r"^(.*?)(_schedule)?_year_1$", "\\1", target_row)
            logger.debug(f"Custom Rule. Replacing: '{target_row}' with '{new_val}'")
        elif re.match(r"^.*?_year_1_other$", target_row):
            new_val = re.sub(
                r"^(.*?)(_schedule)?_year_1_other$", "\\1_other", target_row
            )
            logger.debug(f"Custom Rule. Replacing: '{target_row}' with '{new_val}'")
        elif re.match(r"^.*?(_schedule)?_year_.*$", target_row):
            new_val = re.sub(r"^(.*?)(_schedule)?_year_(.*)$", "\\1_\\3", target_row)
            logger.debug(f"Custom Rule. Replacing: '{target_row}' with '{new_val}'")

    return new_val != target_row, new_val


def get_files(dir, prefix):
    return [
        f
        for f in os.listdir(dir)
        if os.path.isfile(os.path.join(dir, f))
        and f.startswith(prefix)
        and f.endswith(".csv")
    ]


def does_file_exist(filepath):
    return os.path.isfile(filepath)


def clear_and_create_dir(dir):
    if os.path.exists(dir):
        shutil.rmtree(dir)
    os.makedirs(dir)


def get_matching_file(postfix=None):
    if PARENT_DIR == "JKMR":
        if postfix == "site_plans":
            postfix = "break_before_site_plans"
        elif postfix == "site_photo_property":
            postfix = "site_photos_property"
        elif postfix == "knotweed_survey_knotweed_stand_details":
            postfix = "knotweed_stand_details"
        elif postfix == "knotweed_survey_knotweed_stand_details_stand_photos":
            postfix = "knotweed_stand_details_stand_photos"
    elif PARENT_DIR == "JKMR_SV":
        if postfix == "site_visits_re_written":
            postfix = "service_visit_records"
    elif PARENT_DIR == "IPMR_SV":
        if postfix == "service_visits_re_written":
            postfix = "service_visit_records"

    return postfix, os.path.join(
        BASE_DIR, f"{BASE_PREFIX}{('_' + postfix) if postfix else ''}.csv"
    )


def transform_knotweed_survey_repeatable_jkmr():
    # We want to take in a csv file for the knotweed survey repeatable
    # We then want to identify all parent records and read the data for that parent record ID into a dictionary
    # For each record within the survey record, we want to create a new record joined with the parent record data
    # We then want to take these new records and write them to a new csv file
    parent_record_ids = []
    parent_record_data = {}
    child_records_mapping = {}
    with open(
        os.path.join(TARGET_DIR, f"{TARGET_PREFIX}_knotweed_survey.csv"), "r"
    ) as f:
        reader = csv.DictReader(f)
        rows = list(reader)

        for r in rows:
            if r["fulcrum_parent_id"] not in child_records_mapping.keys():
                child_records_mapping[r["fulcrum_parent_id"]] = [r]
            else:
                child_records_mapping[r["fulcrum_parent_id"]].append(r)

    # Get all the data for each parent record
    with open(os.path.join(TARGET_DIR, f"{TARGET_PREFIX}.csv")) as f:
        reader = csv.DictReader(f)
        rows = list(reader)

        # Get all parent records
        parent_record_ids = [r["fulcrum_id"] for r in rows]

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
            new_row = {
                "fulcrum_id": child_record["fulcrum_id"],
                # This is used for the import api script not the Fulcrum import interface
                "fulcrum_parent_id_not_used": child_record["fulcrum_parent_id"],
                **{
                    k: parent_record_data[parent_id][k]
                    for k in parent_record_data[parent_id].keys()
                    if k != "fulcrum_id"
                },
                **{
                    k: child_record[re.sub(r"^child_", "", k)]
                    for k in child_keys
                    if k != "child_fulcrum_id"
                },
            }
            new_rows.append(new_row)

    # Now add all the parent records that don't have any child records
    for parent_id, parent_record in parent_record_data.items():
        if parent_id not in child_records_mapping.keys():
            new_row = {
                "fulcrum_id": parent_record["fulcrum_id"],
                # This is used for the import api script not the Fulcrum import interface
                "fulcrum_parent_id_not_used": parent_record["fulcrum_id"],
                **{
                    k: parent_record[k]
                    for k in parent_record.keys()
                    if k != "fulcrum_id"
                },
            }
            new_rows.append(new_row)

    # Write the new data to a new csv file
    with open(
        os.path.join(TARGET_DIR, f"{TARGET_PREFIX}_base_re_written.csv"),
        "w",
        newline="",
    ) as f:
        writer = csv.DictWriter(f, fieldnames=new_rows[0].keys())
        writer.writeheader()
        writer.writerows(new_rows)


def merge_fields(row, field_key_1, field_key_2):
    """
    Merge two fields together, if the first field is empty, use the second field
    """
    if field_key_1 not in row.keys() and field_key_2 not in row.keys():
        return row
    elif field_key_2 in row.keys() and not row[field_key_1]:
        logger.info(
            f"Field {field_key_1} is empty, using {field_key_2} instead for row {row['fulcrum_id']}"
        )
        row[field_key_1] = row[field_key_2]
        return row
    elif field_key_1 in row.keys() and not row[field_key_2]:
        return row

    return row


def transform_knotweed_survey_stand_details_jkmr():
    new_rows = []

    with open(
        os.path.join(
            TARGET_DIR, f"{TARGET_PREFIX}_knotweed_survey_knotweed_stand_details.csv"
        ),
        "r",
    ) as f:
        reader = csv.DictReader(f)
        rows = list(reader)

        for row in rows:
            old_location_val = row["stand_location_visibly_impacted_areas"]
            old_location_other_val = row["stand_location_visibly_impacted_areas_other"]
            new_location_val = row["visibly_impacted_areas_subject_property"]
            new_location_other_val = row[
                "visibly_impacted_areas_subject_property_other"
            ]

            if (
                old_location_val
                and new_location_val
                and old_location_val != new_location_val
            ):
                logger.info(
                    f"{row['fulcrum_id']}: Both old and new values are populated. Old: '{old_location_val}', New: '{new_location_val}'"
                )
            if (
                old_location_other_val
                and new_location_other_val
                and old_location_other_val != new_location_other_val
            ):
                logger.info(
                    f"{row['fulcrum_id']}: Both old and new other values are populated. Old: '{old_location_other_val}', New: '{new_location_other_val}'"
                )

            if old_location_val:
                row["visibly_impacted_areas_subject_property"] = old_location_val

            if old_location_other_val:
                row[
                    "visibly_impacted_areas_subject_property_other"
                ] = old_location_other_val

            old_distance_val = row["distance_from_nearest_dwelling_m"]
            new_distance_val = row["distance_from_subject_property_dwelling_m"]

            if (
                old_distance_val
                and new_distance_val
                and old_distance_val != new_distance_val
            ):
                logger.info(
                    f"{row['fulcrum_id']}: Both old and new values are populated. Old: '{old_distance_val}', New: '{new_distance_val}'"
                )

            if old_distance_val and not new_distance_val:
                row["distance_from_subject_property_dwelling_m"] = old_distance_val

        new_rows = rows

    with open(
        os.path.join(
            TARGET_DIR,
            f"{TARGET_PREFIX}_knotweed_survey_knotweed_stand_details_re_written.csv",
        ),
        "w",
    ) as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(new_rows)


def transform_base_for_service_visits_ipmr():
    """
    Transform the base app when for an IPMR difference findings when we are
    finding differences for the site visits transformation
    """

    new_rows = []

    with open(os.path.join(TARGET_DIR, f"{TARGET_PREFIX}.csv"), "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

        fields_to_merge = [
            ["property_type", "property_type_other"],
        ]

        for row in rows:
            for field_pair in fields_to_merge:
                row = merge_fields(row, field_pair[0], field_pair[1])
            new_rows.append(row)

    with open(
        os.path.join(TARGET_DIR, f"{TARGET_PREFIX}_base_re_written.csv"),
        "w",
        newline="",
    ) as f:
        writer = csv.DictWriter(f, fieldnames=new_rows[0].keys())
        writer.writeheader()
        writer.writerows(new_rows)


def transform_service_visits_ipmr():
    """
    Transform the service visit records for the IPMR app into individual records that
    have been joined to the parent record
    """

    # Each service visit is an entire record in the new survey app
    # We want to read all the child values and then join them to the parent values
    # to create a new record for each service visit. We should add a new field to say
    # what the parent record id is and map the child record id to the id of the new
    # record

    # To hold the IDs of the parent records
    parent_record_ids = []

    # To hold the values of the parent records
    # We will use the parent record id as the key
    parent_record_data = {}

    # To hold the values of the child records
    # The key will be the parent record id and the value will be a list of child record ids
    parent_to_child_record_mapping = {}

    # To hold the values of the child records
    # The key will be the child record id
    child_record_data = {}

    service_visit_postfix = "_service_visit_records"

    # Read the parent records
    with open(os.path.join(TARGET_DIR, f"{TARGET_PREFIX}.csv"), "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

        for row in rows:
            parent_record_id = row["fulcrum_id"]
            parent_record_ids.append(parent_record_id)
            parent_record_data[parent_record_id] = row

    # Read the child records
    with open(
        os.path.join(TARGET_DIR, f"{TARGET_PREFIX}{service_visit_postfix}.csv"), "r"
    ) as f:
        reader = csv.DictReader(f)
        rows = list(reader)

        for row in rows:
            parent_record_id = row["fulcrum_parent_id"]
            child_record_id = row["fulcrum_id"]

            # Throw an error if the parent record id is not in the list
            if parent_record_id not in parent_record_ids:
                raise Exception(
                    f"Parent record id '{parent_record_id}' does not exist in the list of parent record ids.\n"
                    + "This means that there are child records for a parent record that does not exist.\n"
                    + "This is not allowed."
                )

            # Throw an error if the child record id is already in the list
            if child_record_id in child_record_data:
                raise Exception(
                    f"Child record id '{child_record_id}' already exists in the list of child record ids.\n"
                    + "This means that there are multiple child records with the same id.\n"
                    + "This is not allowed."
                )

            # Add the child record to the list of child records
            child_record_data[child_record_id] = row

            # Add the child record to the mapping of parent record ids to child record ids
            if parent_record_id not in parent_to_child_record_mapping:
                parent_to_child_record_mapping[parent_record_id] = []

            parent_to_child_record_mapping[parent_record_id].append(child_record_id)

    logger.debug("Parent record ids: %s", parent_record_ids)
    logger.debug("Child record ids: %s", child_record_data.keys())
    logger.debug("Parent to child record mapping: %s", parent_to_child_record_mapping)

    # Create a new list of rows
    new_rows = []

    # Loop through the parent records
    for parent_record_id in parent_record_ids:
        parent_record = parent_record_data[parent_record_id]

        # Ignore parent records that don't have any child records
        if parent_record_id not in parent_to_child_record_mapping:
            continue

        # Loop through the child records
        for child_record_id in parent_to_child_record_mapping[parent_record_id]:
            child_record = child_record_data[child_record_id]

            # Create a new row
            new_row = {}

            # Copy the parent record values to the new row
            for key, value in parent_record.items():
                new_row[key] = value

            # Copy the child record values to the new row
            for key, value in child_record.items():
                new_row[key] = value

            # Add a new field to the new row to say what the parent record id is
            new_row["fulcrum_parent_id"] = parent_record_id

            # Add the new row to the list of new rows
            new_rows.append(new_row)

    # Write the new rows to a new CSV file
    with open(
        os.path.join(TARGET_DIR, f"{TARGET_PREFIX}_service_visits_re_written.csv"),
        "w",
        newline="",
    ) as f:
        writer = csv.DictWriter(f, fieldnames=new_rows[0].keys())
        writer.writeheader()
        writer.writerows(new_rows)


def transform_site_visits():
    new_csv = []

    # This is for just visualising the data
    fields_to_fill = {
        # All the child fields of each parent key here will be filled with the value of the parent key
        "technician_details_qualifications": [
            "surveyortechnician_names",  # surveyortechnician_names will then be filled with the value of technician_details_qualifications
            "technicians_names",  # technicians_names will then be filled with the value of technician_details_qualifications
        ],
        "technician_details_qualifications_other": [
            "surveyortechnician_names_other",
            "technicians_names_other",
        ],
        "time": ["treatment_start_time"],
        "date": ["treatment_date", "information_date"],
        "does_site_to_be_treated_meet_generic_rams_criteria": [
            "does_site_meet_raams_criteria",
            "does_site_for_treatment_meet_generic_rams_criteria",
        ],
    }

    # This is for actually filling the data as the key lookup is more efficient
    # Every child of each parent key is the now the key where the value of this key is the parent key
    inverted_mapping = {vv: k for k, v in fields_to_fill.items() for vv in v}

    # TODO: Uncomment when the other sections are ready in the SITE VISITS APP
    # visit_files = ["herbicide_application_monitoring_records",
    #                "other_treatments_inc_excavation",
    #                "site_monitoring_observations_and_recommendations"]
    visit_files = [
        "herbicide_application_monitoring_records",
        "site_monitoring_observations_and_recommendations",
    ]

    file_to_value_mapping = {
        "herbicide_application_monitoring_records": "Herbicide Application & Monitoring Record",
        "other_treatments_inc_excavation": "Other Treatments Inc. Excavation",
        "site_monitoring_observations_and_recommendations": "Site Monitoring Observations & Recommendations",
    }

    # This is a new header based on the name of the repeatable but it also matches
    # to a new column in the new site visit app
    all_headers = ["record_type_japanese_knotweed"]

    for visit_file in visit_files:
        with open(
            os.path.join(TARGET_DIR, f"{TARGET_PREFIX}_{visit_file}.csv"), "r"
        ) as f:
            csv_content = csv.DictReader(f)
            rows = list(csv_content)

            headers = csv_content.fieldnames
            all_headers.extend([k for k in headers if k not in all_headers])

            for row in rows:
                # Assign the record type to what repeatable the record came from
                row["record_type_japanese_knotweed"] = file_to_value_mapping[visit_file]

                for header in headers:
                    if header not in row:
                        row[header] = ""

                    if header in inverted_mapping and row[header]:
                        row[inverted_mapping[header]] = row[header]

            if len(rows) == 0:
                continue

            new_csv.extend(rows)

    with open(
        os.path.join(TARGET_DIR, f"{TARGET_PREFIX}_site_visits_re_written.csv"), "w"
    ) as f:
        writer = csv.DictWriter(f, fieldnames=all_headers)
        writer.writeheader()
        writer.writerows(new_csv)


def find_and_write_diffs(base, target, prefix):
    # Find differences
    diff = [f for f in target if f not in base]

    # Find matches
    # matches = [f for f in target if f in base]

    # Find unmatched
    unmatched = [f for f in base if f not in target]

    # Find closest matches
    closest_matches = [
        difflib.get_close_matches(f, unmatched, n=1, cutoff=0) for f in diff
    ]

    rows = list(
        zip(
            diff,
            ["N/A" if not f else f[0] for f in closest_matches],
            ["" for f in closest_matches],
        )
    )

    # Create table
    table = create_table(rows)

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
                logger.debug(f"Replacing: '{row[0]}' with '{mappings[row[0]]}'")
                rows[i] = [row[0], row[1], mappings[row[0]]]
                if mappings[row[0]] in unmatched:
                    unmatched.remove(mappings[row[0]])
                continue
            elif mappings_exist:
                logger.debug(f"Skipping: '{row[0]}'")
                continue

            changed, new_val = apply_custom_rules(row[0])

            if changed:
                rows[i] = [row[0], row[1], new_val]
                if new_val in unmatched:
                    unmatched.remove(new_val)
                mappings[row[0]] = new_val
            else:
                if SKIP_PROMPT_MATCHING:
                    continue

                logger.info(
                    f"Replace:\n{row[0]}\nSuggested: {row[1]}? (Y/n/type your own column name)"
                )
                response = input()
                response = response.lower().strip()

                if response == "y" or response == "":
                    # Replace column
                    logger.info(f"Replacing: '{row[0]}' with '{row[1]}'")
                    rows[i] = [row[0], row[1], row[1]]
                    if row[1] in unmatched:
                        unmatched.remove(row[1])
                    mappings[row[0]] = row[1]
                elif response == "n":
                    logger.info(f"Skipping: '{row[0]}'")
                    continue
                else:
                    if response not in unmatched:
                        logger.warning(f"Invalid column: '{response}'")
                        continue
                    logger.info(f"Replacing: '{row[0]}' with '{response}'")
                    rows[i] = [row[0], row[1], response]
                    if response in unmatched:
                        unmatched.remove(response)
                    mappings[row[0]] = response

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


def get_correct_file_name(f):
    if f == f"{TARGET_PREFIX}.csv":
        if PARENT_DIR == "JKMR":
            return f"{TARGET_PREFIX}_base_re_written.csv"
        else:
            return f
    elif f == f"{TARGET_PREFIX}_service_visit_records.csv":
        if PARENT_DIR == "IPMR_SV":
            return f"{TARGET_PREFIX}_service_visits_re_written.csv"

    return f


# Main

if not os.path.exists(f"{BASE_PARENT_DIR}"):
    os.makedirs(f"{BASE_PARENT_DIR}")

delete_mismatch_file()

if PARENT_DIR == "JKMR":
    # This re-writes some repeatables so it can match the survey
    transform_knotweed_survey_repeatable_jkmr()
    transform_knotweed_survey_stand_details_jkmr()

if PARENT_DIR == "JKMR_SV":
    transform_site_visits()

if PARENT_DIR == "IPMR_SV":
    transform_base_for_service_visits_ipmr()
    transform_service_visits_ipmr()

# Read all the files in the base & target directory
base_files = get_files(BASE_DIR, BASE_PREFIX)

target_files = []

if re.search(r"_SV$", PARENT_DIR):
    # We only check the base and the re-written site visits when we are doing a site visits comparison
    target_files = [
        f"{TARGET_PREFIX}.csv",
        f"{TARGET_PREFIX}_site_visits_re_written.csv"
        if PARENT_DIR == "JKMR"
        else f"{TARGET_PREFIX}_service_visits_re_written.csv",
    ]
else:
    target_files = get_files(TARGET_DIR, TARGET_PREFIX)

# Loop through each target file, find the base equivalent and compare
for f in target_files:
    # Skip these files
    if (
        PARENT_DIR == "JKMR"
        and (
            f == f"{TARGET_PREFIX}_base_re_written.csv"
            or f == f"{TARGET_PREFIX}_knotweed_survey.csv"
        )
    ) or (
        PARENT_DIR == "IPMR" and f == f"{TARGET_PREFIX}_service_visits_re_written.csv"
    ):
        continue

    # Sometimes we want to use a different file name, this functions provides those mappings
    target_f = get_correct_file_name(f)

    # If the file is the prefix then this is the parent file
    if f == f"{TARGET_PREFIX}.csv":
        new_postfix, base_filepath = get_matching_file()

        does_base_file_exist = does_file_exist(base_filepath)

        # If the base file doesn't exist then raise an exception
        if not does_base_file_exist:
            write_file_no_match(base_filepath)

        # Read the files
        base_rows = read_csv_columns(base_filepath) if does_base_file_exist else []
        target_rows = read_csv_columns(os.path.join(TARGET_DIR, target_f))

        # Find and write differences
        find_and_write_diffs(
            base_rows, target_rows, "base" if does_base_file_exist else "NO_MATCH_base"
        )
    else:
        # These are the child repeatables
        # Grab the postfix
        postfix = f.replace(f"{TARGET_PREFIX}_", "").replace(".csv", "")

        # Base filepath
        new_postfix, base_filepath = get_matching_file(postfix)

        does_base_file_exist = does_file_exist(base_filepath)

        # If the base file doesn't exist then raise an exception
        if not does_base_file_exist:
            write_file_no_match(base_filepath)

        # Read the files
        base_rows = read_csv_columns(base_filepath) if does_base_file_exist else []
        target_rows = read_csv_columns(os.path.join(TARGET_DIR, target_f))

        # Find and write differences
        find_and_write_diffs(
            base_rows,
            target_rows,
            new_postfix.lower()
            if does_base_file_exist
            else "NO_MATCH_" + new_postfix.lower(),
        )

logger.info("Success")
