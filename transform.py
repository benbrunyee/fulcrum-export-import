import argparse
import csv
import os
import re
import shutil

# Arguments
parser = argparse.ArgumentParser(description="Find differences between 2 csv files")

parser.add_argument("--parent_dir", type=str, help="Parent directory", required=True)
parser.add_argument("--target_dir", type=str, help="Target directory", required=True)
parser.add_argument("--target_prefix", type=str, help="Target prefix", required=True)
parser.add_argument(
    "--site_location_file", type=str, help="Site location file", required=True
)
parser.add_argument(
    "--client_name_col", type=str, help="Client name column", required=True
)
parser.add_argument(
    "--acc_ref_col", type=str, help="Account reference column", required=True
)
parser.add_argument("--transform_type", type=str, help="Transform type", required=True)
parser.add_argument("--survey_dir", type=str, help="Survey directory")
parser.add_argument("--survey_dir_prefix", type=str, help="Survey directory prefix")

args = parser.parse_args()


# Constants

PARENT_DIR = args.parent_dir
BASE_PARENT_DIR = f"new_files\\{PARENT_DIR}"

TARGET_DIR = args.target_dir
TARGET_PREFIX = args.target_prefix

SURVEY_DIR = args.survey_dir
SURVEY_DIR_PREFIX = args.survey_dir_prefix

CLIENT_NAME_COL = args.client_name_col
ACC_REF_COL = args.acc_ref_col

SITE_LOCATION_FILE = args.site_location_file

TRANSFORM_TYPE = args.transform_type

TRANSFORMATIONS = {
    "KSMP": {},
    "JKMR": {
        "knotweed_stand_details": {
            "stand_location": {
                "Within client property only": "Site only",
                "Within client property and one other property": "Site and one adjacent property",
                "Within client property and more than one other property": "Site and more than one other property",
                "Within an adjacent property only": "One adjacent property only",
                "Within more than one adjacent property": "More than one other property only",
            }
        },
        "base": {
            "jk_package_type": {
                "kmp": "Contracted (Knotweed Management Plan)",
                "payg": "Non-contract (Pay As You Go)",
                "jk_identification_survey_&_report": "Knotweed identification survey and findings report",
                "jk_survey_&_findings_report": "JK Survey & Findings Report",
                "jk_mcp": "JK MCP",
                "jk_payg": "JK PAYG",
            }
        },
    },
}

PROPERTY_TYPE_MAPPINGS = {
    "Private Residential": "Residential",
    "Housing Association": "Residential",
    "Commercial": "Residential",
    "Council": "Residential",
    "Education": "Residential",
    "Healthcare": "Residential",
    "Industrial": "Residential",
}

DEFAULT_BASE_COLS = {
    "record_type": lambda row: "Management Plan",
    "client_type": lambda row: PROPERTY_TYPE_MAPPINGS[
        [k for k in PROPERTY_TYPE_MAPPINGS.keys() if re.match(k, row["property_type"])][
            0
        ]
    ]
    if any([re.match(k, row["property_type"]) for k in PROPERTY_TYPE_MAPPINGS.keys()])
    else "",
    "plant_type": lambda row: "Other" if PARENT_DIR == "IPMR" else "Japanese Knotweed",
    "job_type": lambda row: "Treatment",
}

DEFAULT_SV_SV_COLS = {
    "visit_category": lambda row: "Japanese Knotweed Management Record",
    "record_type_japanese_knotweed": lambda row: row["record_type_japanese_knotweed"]
    if "record_type_japanese_knotweed" in row
    else "Herbicide Application & Monitoring Record",
    "visit_type_japanese_knotweed_application_monitoring": lambda row: row["visit_type"]
    if row["visit_type"] != "Site Monitoring Observations & Recommendations"
    else "Scheduled Monitoring",
}


# Functions


def read_csv(file_path):
    """Read a csv file and return a list of rows"""
    with open(file_path, "r") as f:
        reader = csv.DictReader(f)
        return list(reader)


def get_files(dir):
    return [
        f
        for f in os.listdir(dir)
        if os.path.isfile(os.path.join(dir, f)) and f.endswith(".csv")
    ]


def get_dirs(dir):
    return [f for f in os.listdir(dir) if os.path.isdir(os.path.join(dir, f))]


def does_file_exist(filepath):
    return os.path.isfile(filepath)


def clear_and_create_dir(dir):
    if os.path.exists(dir):
        shutil.rmtree(dir)
    os.makedirs(dir)


def transform(diff_dir_name, target_csv_name):
    is_survey_transform = TRANSFORM_TYPE == "survey"
    is_site_visits_transform = TRANSFORM_TYPE == "site_visits"

    diff = read_csv(f"{BASE_PARENT_DIR}\\differences\\{diff_dir_name}\\differences.csv")
    cols = [f["Column"] for f in diff]

    data = read_csv(
        f"{TARGET_DIR}\\{TARGET_PREFIX}_{target_csv_name}.csv"
        if target_csv_name != "base"
        else f"{TARGET_DIR}\\{TARGET_PREFIX}.csv"
    )

    new_cols = list(data[0].keys() if len(data) > 0 else [])

    # Update columns
    for i, orig_col in enumerate(new_cols):
        if orig_col not in cols:
            continue

        found_i = cols.index(orig_col)
        val = diff[found_i]["Updated"].strip()

        if val == "" or val == "N/A":
            continue

        # print(f"Replacing {new_cols[i]} with {val}")
        new_cols[i] = val

    if is_site_visits_transform:
        # Find the survey ID for the site visit
        # Match on the Job ID and the site address
        for row in data:
            # Set defaults
            if diff_dir_name == "service_visit_records":
                for col, func in DEFAULT_SV_SV_COLS.items():
                    row[col] = func(row)

    if is_survey_transform:
        site_location_csv = read_csv(SITE_LOCATION_FILE)

        site_address_checks = [
            "site_address_postal_code",
            "site_address_thoroughfare",
            "site_address_sub_thoroughfare",
            "site_address_locality",
            "site_address_admin_area",
            "site_address_country",
        ]

        # Match on site full address, client name and job id write this to the end file for the "site_location" link
        for row in data:
            if diff_dir_name == "base":
                found = False

                for site_location in site_location_csv:
                    match = False

                    for check in site_address_checks:
                        if row[check] != site_location[check]:
                            match = False
                            break
                        else:
                            match = True

                    if (
                        match
                        and row[CLIENT_NAME_COL].strip() == site_location["client_name"]
                        and row[ACC_REF_COL] == site_location["job_id"]
                    ):
                        row["site_location"] = site_location["fulcrum_id"]
                        found = True
                        break

                if not found:
                    raise Exception(
                        f"Could not find site location: {row['fulcrum_id']}"
                    )

                # Set default columns
                for col, func in DEFAULT_BASE_COLS.items():
                    row[col] = func(row)

            for k, v in row.items():
                if (
                    diff_dir_name in TRANSFORMATIONS[PARENT_DIR]
                    and k in TRANSFORMATIONS[PARENT_DIR][diff_dir_name]
                    and v in TRANSFORMATIONS[PARENT_DIR][diff_dir_name][k]
                ):
                    row[k] = TRANSFORMATIONS[PARENT_DIR][diff_dir_name][k][v]

    with open(
        f"{BASE_PARENT_DIR}\\new_records\\{diff_dir_name}.csv", "w", newline=""
    ) as f:
        headers = []

        if is_survey_transform:
            headers = [
                *new_cols,
                "site_location",
                *(
                    list(filter(lambda x: x not in new_cols, DEFAULT_BASE_COLS.keys()))
                    if diff_dir_name == "base"
                    else []
                ),
            ]
        else:
            headers = [
                *new_cols,
                *(
                    list(filter(lambda x: x not in new_cols, DEFAULT_SV_SV_COLS.keys()))
                    if diff_dir_name == "service_visit_records"
                    else []
                ),
            ]

        writer = csv.writer(f, strict=True)
        writer.writerow(headers)

        rows = [list(f.values()) for f in data]
        writer.writerows(rows)


def get_file_mapping(dir_name):
    if PARENT_DIR == "JKMR":
        if dir_name == "break_before_site_plans":
            dir_name = "site_plans"
        elif dir_name == "site_photos_property":
            dir_name = "site_photo_property"
        elif dir_name == "knotweed_stand_details":
            dir_name = "knotweed_survey_knotweed_stand_details_re_written"
        elif dir_name == "knotweed_stand_details_stand_photos":
            dir_name = "knotweed_survey_knotweed_stand_details_stand_photos"
        elif dir_name == "base":
            dir_name = "base_re_written"
    if PARENT_DIR == "JKMR_SV":
        if dir_name in "service_visit_records":
            dir_name = "site_visits_re_written"

    return dir_name


# Main

if TRANSFORM_TYPE not in ["survey", "site_visits"]:
    raise Exception("Invalid transform type")

if TRANSFORM_TYPE == "site_visits" and not (SURVEY_DIR and SURVEY_DIR_PREFIX):
    raise Exception(
        "Missing survey export params, please set --survey_dir and --survey_dir_prefix"
    )

clear_and_create_dir(f"{BASE_PARENT_DIR}\\new_records")

for diff_dir_name in get_dirs(f"{BASE_PARENT_DIR}\\differences"):
    if diff_dir_name.startswith("NO_MATCH_"):
        continue

    target_csv_name = get_file_mapping(diff_dir_name)
    transform(diff_dir_name, target_csv_name)

print("Success")
