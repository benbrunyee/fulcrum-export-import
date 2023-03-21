import argparse
import csv

parser = argparse.ArgumentParser(description="Find differences between 2 csv files")
parser.add_argument("--survey_dir", type=str, help="Survey directory", required=True)
parser.add_argument("--survey_prefix", type=str, help="Survey prefix", required=True)
parser.add_argument("--target_file_path", type=str, help="Target file path", required=True)

args = parser.parse_args()

# Constants
SURVEY_DIR = args.survey_dir
SURVEY_PREFIX = args.survey_prefix

TARGET_FILE_PATH = args.target_file_path

# Functions

def read_csv_file(file):
    headers = []
    rows = []

    with open(file, 'r') as f:
        reader = csv.DictReader(f, strict=True)
        headers = [header for header in reader.fieldnames]

        rows = [row for row in reader]

    return headers, rows

# Main

# Read in the survey data
survey_headers, survey_rows = read_csv_file(f"{SURVEY_DIR}\\{SURVEY_PREFIX}.csv")

# Read in the target data
target_headers, target_rows = read_csv_file(TARGET_FILE_PATH)
