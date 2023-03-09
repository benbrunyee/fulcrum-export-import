import argparse
import csv
import os
import re

# Arguments
parser = argparse.ArgumentParser(
    description="Create clientele list for import")

parser.add_argument("--existing_clientele", type=str,
                    help="Existing clientele file", required=False)
parser.add_argument("--target_file", type=str,
                    help="Target file for finding clientele", required=True)
parser.add_argument("--ref_col", type=str,
                    help="Reference column name", required=True)
parser.add_argument("--client_name_col", type=str,
                    help="Client name column name", required=True)

args = parser.parse_args()

# Constants

EXISTING_CLIENTELE = args.existing_clientele
TARGET_FILE = args.target_file
REF_COL_NAME = args.ref_col
CLIENT_NAME_COL = args.client_name_col
ID_COL = "fulcrum_id"

EXISTING_CLIENT_COL_NAME = "client_name"

MISSING_CLIENT_NAMES_FILE = "new_files\\empty_client_names_" + \
    re.sub(r"\.csv", "", TARGET_FILE.split('\\')[-1]) + ".txt"

# Main

if not os.path.exists("new_files"):
    os.makedirs("new_files")

if os.path.exists(MISSING_CLIENT_NAMES_FILE):
    os.remove(MISSING_CLIENT_NAMES_FILE)

client_names = []
acc_refs = []
existing_names = []

client_details = {}

# Read the existing clientele file
if EXISTING_CLIENTELE and os.path.exists(EXISTING_CLIENTELE) and os.path.getsize(EXISTING_CLIENTELE) > 0:
    with open(EXISTING_CLIENTELE, 'r') as f:
        reader = csv.DictReader(f)

        for row in reader:
            existing_names.append(row[EXISTING_CLIENT_COL_NAME])

# Read the file using csv
with open(TARGET_FILE, 'r') as f:
    reader = csv.DictReader(f)

    for row in reader:
        # Find account reference and client name
        # Highlight duplicates
        client_name = row[CLIENT_NAME_COL].strip()

        if client_name in existing_names:
            # This client name already exists
            print(
                f"ID: {row[ID_COL]}, Client name already exists: {client_name}, Account reference: {row[REF_COL_NAME]}")
            continue

        if not client_name:
            # This is important
            print(
                f"ID: {row[ID_COL]}, Client name is empty, Account reference: {row[REF_COL_NAME]}")
            open(MISSING_CLIENT_NAMES_FILE, 'a').write(
                f"Account reference: {row[REF_COL_NAME]}: Missing client name\n")

        if client_name in client_names:
            # This is not important
            print(
                f"ID: {row[ID_COL]}, Duplicate client name: {client_name}, Account reference: {row[REF_COL_NAME]}")
        else:
            client_names.append(client_name)

        if row[REF_COL_NAME] in acc_refs:
            # This is not important
            print(
                f"ID: {row[ID_COL]}, Duplicate account reference: {row[REF_COL_NAME]}, Client: {client_name}")
        else:
            acc_refs.append(row[REF_COL_NAME])

        if client_name not in client_details:
            client_details[client_name] = [row[REF_COL_NAME]]
        else:
            client_details[client_name].append(row[REF_COL_NAME])

# Print the client details
# for client in client_details:
#     print(f"Client: {client}, Account references: {client_details[client]}")

# Write the client names to a file
with open("new_files\\new_client_names.csv", 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["client_name"])
    for client in client_names:
        writer.writerow([client])
