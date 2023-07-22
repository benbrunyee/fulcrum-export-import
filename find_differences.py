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
    elif PARENT_DIR == "IPMR":
        if postfix == "stand_details_re_written":
            postfix = "stand_details"
    elif PARENT_DIR == "IPMR_SV":
        if postfix == "service_visit_records_re_written":
            postfix = "service_visit_records"
    elif PARENT_DIR == "S":
        if postfix == "knotweed_stand_details":
            postfix = "stand_details"
        elif postfix == "knotweed_stand_details_stand_photos":
            postfix = "stand_details_stand_photos"
        elif (
            postfix
            == "knotweed_stand_details_hide_stand_shape_and_area_capture_point_data"
        ):
            postfix = "stand_details_hide_stand_shape_and_area_capture_point_data"

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


def merge_fields(row, field_key_1, field_key_2, allow_multiple=False):
    """
    Merge two fields together, if the first field is empty, use the second field.
    If allow_multiple is defined, then add the second field to the first field, separated by a comma.
    """
    if field_key_1 not in row.keys() or field_key_2 not in row.keys():
        raise Exception(
            f"Field {field_key_1} or {field_key_2} not found in row {row['fulcrum_id']}"
        )
    elif not row[field_key_1]:
        logger.info(
            f"Field {field_key_1} is empty, using {field_key_2} instead for row {row['fulcrum_id']}"
        )
        row[field_key_1] = row[field_key_2]
        return row
    elif allow_multiple and row[field_key_1] and row[field_key_2]:
        row[field_key_1] = f"{row[field_key_1]},{row[field_key_2]}"
        return row

    return row


def map_fields(row, field_map):
    """
    Map fields to a new field name
    """
    for old_field, new_field in field_map.items():
        if old_field not in row.keys():
            raise Exception(f"Field {old_field} not found in row {row['fulcrum_id']}")

        row[new_field] = row[old_field]

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


def transform_base_ipmr():
    new_rows = []
    with open(os.path.join(TARGET_DIR, f"{TARGET_PREFIX}.csv"), "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

        # Remove the quotations from the following fields
        fields_to_remove_quotations = [
            "surveyors_and_qualifications",
            "surveyors_and_qualifications_other",
        ]

        for row in rows:
            for field in fields_to_remove_quotations:
                row[field] = row[field].replace('"', "")

            new_rows.append(row)

    with open(
        os.path.join(TARGET_DIR, f"{TARGET_PREFIX}_base_re_written.csv"),
        "w",
        newline="",
    ) as f:
        writer = csv.DictWriter(f, fieldnames=new_rows[0].keys())
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
    Transform the base app when for an IPMR difference findings when we are
    finding differences for the site visits transformation and site visits
    repeatable
    """
    new_rows = []
    with open(
        os.path.join(TARGET_DIR, f"{TARGET_PREFIX}_service_visit_records.csv"),
        "r",
    ) as f:
        reader = csv.DictReader(f)
        rows = list(reader)

        # regex for key
        service_type_to_visit_type_data_name_map = {
            "Herbicide treatment .*": "visit_type_invasive_plants_application",
            ".*": "visit_type_invasive_plants_other",
        }

        fields_to_merge = [
            {
                "type": "allow_multiple",
                "fields": [
                    # We purposefully ignore the service_visit_type field
                    ["adjuvant_name", "adjuvant_name_other"],
                ],
            },
            {
                "type": "single",
                "fields": [],
            },
        ]

        for row in rows:
            row_handled = False

            # ==================
            for obj_type in fields_to_merge:
                for field_pair in obj_type["fields"]:
                    if obj_type["type"] == "allow_multiple":
                        row = merge_fields(
                            row, field_pair[0], field_pair[1], allow_multiple=True
                        )
                    else:
                        row = merge_fields(row, field_pair[0], field_pair[1])
            # ==================

            # ==================
            # The "service_type" field is a multiple-choice field but we are trying
            # to map it to a single-choice field in the new app. So we need to create a
            # new row (record) for each  alue and then merge them into a single field
            # We don't want to merge all the fields, just the relevant ones for each
            # value in the multiple choice.

            # Define what section has what data_names so we can split a row and only
            # keep the relevant data for each selected option
            # regex for key
            # If there is a data name with a value set, this is because the value is of
            # a dataname that is shared between the section types. We map this so that
            # we can later set the relevant values for the data names once we have split
            # the rows into multiple rows based on the section type. These are fields
            # like: "notes", "photos", "video"
            section_types = {
                # Herbicide Application
                "Herbicide treatment .*": {
                    "weather_conditions": None,
                    "local_environment_risk_assessment_for_pesticides_if_appropriate_list_proximity_of_buffer_zones_water_courses_etc_": None,
                    "treatment_carried_out": None,
                    "reasons_for_treatment_not_taking_place_or_treatment_interrupted": None,
                    "target_species": None,
                    "treatment_types": None,
                    "reason_for_treatment": None,
                    "product_name_mapp_number_active_ingredient": None,
                    "quantity_of_product_per_litre_ml": None,
                    "total_mix_applied_l": None,
                    "total_active_ingredient_applied_ml": None,
                    "adjuvant_included_in_mix": None,
                    "adjuvant_name": None,
                    "ppe_worn": None,
                    "treatment_notes_observations_and_issues": None,
                    "treatment_photos": None,
                    "treatment_photos_caption": None,
                    "treatment_photos_url": None,
                    "treatment_video": None,
                    "treatment_video_caption": None,
                    "treatment_video_url": None,
                },
                # Site Monitoring
                "Monitoring visit": {
                    "is_new_growth_visible": None,
                    "location_of_visible_growth": None,
                    "describe_the_visible_growth": None,
                    "was_the_visible_growth_treated": None,
                    "reason_for_treatment_not_taking_place": None,
                    "has_host_soil_been_disturbed_or_cultivated": None,
                    "has_host_soil_been_covered_by_any_new_artefactsfeaturesconstruction": None,
                    "has_any_new_soft_or_hard_landscaping_occurred_within_the_impacted_area": None,
                    "other_findingscomments": None,
                    "recommendations": None,
                    "monitoring_photos": None,
                    "monitoring_photos_caption": None,
                    "monitoring_photos_url": None,
                    "monitoring_video": None,
                    "monitoring_video_caption": None,
                    "monitoring_video_url": None,
                },
                # Cut / Clearance / Excavation / Barrier / Other
                ".*": {
                    "service_activity_types": None,
                    "planned_works_completed": None,
                    "works_notes": "treatment_notes_observations_and_issues",
                    "works_audio_record": None,
                    "works_photo_record": "treatment_photos",
                    "works_photo_record_caption": "treatment_photos_caption",
                    "works_photo_record_url": "treatment_photos_url",
                    "works_video_record": "treatment_video",
                    "works_video_record_caption": "treatment_video_caption",
                    "works_video_record_url": "treatment_video_url",
                },
            }

            service_visit_data_names = [
                "service_type",
                "service_type_other",
            ]
            all_selected = []
            for data_name in service_visit_data_names:
                if data_name in row and row[data_name] != "":
                    all_selected.extend(row[data_name].split(","))
            logger.debug("All selected service visit types: %s", all_selected)
            if len(all_selected) > 1:
                logger.debug(
                    "Creating new rows for each selected option: %s. (1 row -> %s rows)",
                    row["fulcrum_id"],
                    len(all_selected),
                )
                for service_visit_data_name in service_visit_data_names:
                    selected_options = [
                        f.strip() for f in row[service_visit_data_name].split(",")
                    ]

                    has_regex_match = False
                    for selected_option in selected_options:
                        if selected_option == "":
                            continue

                        for regex in section_types.keys():
                            if re.match(regex, selected_option):
                                has_regex_match = True
                                break

                        if not has_regex_match:
                            raise Exception(
                                "No regex match for selected option: %s",
                                selected_option,
                            )

                        logger.debug(
                            "Creating new row for selected option: %s", selected_option
                        )

                        copy_row = row.copy()

                        # Set the other service_visit_data_names to an empty string
                        # This is because we want to keep all the data except ones that are
                        # relevant to other section types. For example, if the section type is
                        # "Herbicide treatment" we want to keep all the data except the data
                        # that is relevant to "Monitoring visit" and "Cut / Clearance / Excavation / Barrier / Other"
                        # This is because we are creating a new row for each selected option
                        # and we want to keep all the data except the data that is relevant
                        # to other section types.
                        for data_name in service_visit_data_names:
                            if data_name != service_visit_data_name:
                                copy_row[data_name] = ""

                        # There are some data names that are shared between service types but we
                        # need to determine what values should fill these data names. This is
                        # provided in the dictionary (if there is a value associated with a data name)
                        for (
                            service_type_regex_key,
                            service_type_data_name_object_value,
                        ) in section_types.items():
                            # Check what section this row is relevant to
                            if not re.match(service_type_regex_key, selected_option):
                                continue

                            # This is a match so we can continue
                            for (
                                data_name,
                                data_name_target,
                            ) in service_type_data_name_object_value.items():
                                if not data_name_target:
                                    continue

                                copy_row[data_name_target] = copy_row[data_name]

                        # Set the value of the selected option to the data_name for the section type
                        copy_row[service_visit_data_name] = selected_option

                        # Add the new row to the new_rows array
                        new_rows.append(copy_row)

                        # We no longer want to add the original row to the new_rows array
                        row_handled = True
            # ==================

            if not row_handled:
                new_rows.append(row)

    # regex for key
    service_type_to_record_type_map = {
        "Herbicide treatment .*": "Herbicide Application",
        "Monitoring visit": "Site Monitoring",
        ".*": "Cut / Clearance / Excavation / Barrier / Other",
    }
    for row in new_rows:
        # ==================
        # Find first matching regex and set the record type
        is_match = False
        for regex in service_type_to_record_type_map.keys():
            selected_options = [f.strip() for f in row["service_type"].split(",")]

            for selected_option in selected_options:
                if re.match(regex, selected_option):
                    is_match = True
                    row[
                        "record_type_invasive_plants"
                    ] = service_type_to_record_type_map[regex]
                    break

            if is_match:
                break

        # If no match, set the last record type
        if not is_match:
            row["record_type_invasive_plants"] = service_type_to_record_type_map[
                service_type_to_record_type_map.keys()[-1]
            ]
        # Populate the row with all the visit type data names
        for visit_type_data_name in service_type_to_visit_type_data_name_map.values():
            row[visit_type_data_name] = ""

        # Find the first matching regex and create a new field with the visit type data name
        is_match = False
        for regex in service_type_to_visit_type_data_name_map.keys():
            if re.match(regex, row["service_type"]):
                row[service_type_to_visit_type_data_name_map[regex]] = (
                    row["service_type"]
                    if row["service_type"] != ""
                    else row["service_type_other"]
                )
                is_match = True
                break

        # If no match, set the last visit type data name
        if not is_match:
            row[service_type_to_visit_type_data_name_map.keys()[-1]] = (
                row["service_type"]
                if row["service_type"] != ""
                else row["service_type_other"]
            )
        # ==================

    with open(
        os.path.join(
            TARGET_DIR, f"{TARGET_PREFIX}_service_visit_records_re_written.csv"
        ),
        "w",
        newline="",
    ) as f:
        writer = csv.DictWriter(f, fieldnames=new_rows[0].keys())
        writer.writeheader()
        writer.writerows(new_rows)


def transform_stand_details_ipmr():
    """
    Transform the stand_details repeatable in the IPMR app
    """
    new_rows = []

    with open(os.path.join(TARGET_DIR, f"{TARGET_PREFIX}_stand_details.csv"), "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

        for row in rows:
            # ==================
            # Write the "close_to_water_within_2_metres" value based on the value
            # of the "distance_from_stand_to_water_body" value
            distance = row["distance_from_stand_to_water_body"]
            if distance:
                if distance == "<= 2 metres":
                    row["close_to_water_within_2_metres"] = "Yes"
                else:
                    row["close_to_water_within_2_metres"] = "No"
            else:
                row["close_to_water_within_2_metres"] = ""
            # ==================

            new_rows.append(row)

    with open(
        os.path.join(TARGET_DIR, f"{TARGET_PREFIX}_stand_details_re_written.csv"),
        "w",
        newline="",
    ) as f:
        writer = csv.DictWriter(f, fieldnames=new_rows[0].keys())
        writer.writeheader()
        writer.writerows(new_rows)


def transform_site_visits_jkmr():
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
        if PARENT_DIR == "JKMR" or PARENT_DIR == "IPMR" or PARENT_DIR == "IPMR_SV":
            return f"{TARGET_PREFIX}_base_re_written.csv"
    elif f == f"{TARGET_PREFIX}_stand_details.csv":
        if PARENT_DIR == "IPMR":
            return f"{TARGET_PREFIX}_stand_details_re_written.csv"

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
    transform_site_visits_jkmr()

if PARENT_DIR == "IPMR":
    transform_base_ipmr()
    transform_stand_details_ipmr()

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
        else f"{TARGET_PREFIX}_service_visit_records_re_written.csv",
    ]
else:
    target_files = get_files(TARGET_DIR, TARGET_PREFIX)

# Loop through each target file, find the base equivalent and compare
for f in target_files:
    # Skip these files
    if (
        PARENT_DIR == "JKMR"
        and (
            # ? Not sure why we skip on the re-written base file
            # ? Anyways, this work is done so maybe we can ignore this
            # ? logic
            f == f"{TARGET_PREFIX}_base_re_written.csv"
            or f == f"{TARGET_PREFIX}_knotweed_survey.csv"
        )
    ) or (PARENT_DIR == "IPMR" and f == f"{TARGET_PREFIX}_stand_details.csv"):
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
