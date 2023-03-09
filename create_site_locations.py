import argparse
import csv
import os

# Arguments

parser = argparse.ArgumentParser(
    description="Create site locations for import")
parser.add_argument("--existing_site_locations", type=str,
                    help="Existing site locations file", required=False)
parser.add_argument("--clientele_file", type=str,
                    help="Clientele file", required=True)
parser.add_argument("--target_file", type=str,
                    help="Target file for finding site locations", required=True)
parser.add_argument("--client_name_col", type=str,
                    help="Client name column name", required=True)
parser.add_argument("--acc_ref_col", type=str,
                    help="Account reference column name", required=True)
parser.add_argument("--property_type_col", type=str,
                    help="Property type column name", required=True)
parser.add_argument("--account_status_col", type=str,
                    help="Account status column name", required=True)
parser.add_argument("--site_address_prefix", type=str,
                    help="Site address prefix", required=True)

args = parser.parse_args()

# Read in existing locations
# If we come across a row within the target file that is listing a location, client reference and client name to one that already exists, then we don't need to add this to the new file
# We can simply skip. Otherwise, we do add it so that it can be imported

# Constants

if not os.path.exists("new_files"):
    os.makedirs("new_files")

EXISTING_SITE_LOCATIONS = args.existing_site_locations

CLIENTELE = args.clientele_file
TARGET_FILE = args.target_file

ID_COL = "fulcrum_id"
CLIENT_NAME_COL = args.client_name_col
ACC_REF_COL = args.acc_ref_col
PROPERTY_TYPE_COL = args.property_type_col
ACCOUNT_STATUS_COL = args.account_status_col

EXISTING_CLIENT_NAME_COL = "client_name"
EXISTING_ACC_REF_COL = "job_id"
EXISTING_SITE_ADDRESS_PREFIX = "site_address_"

site_address_prefix = args.site_address_prefix
site_address_postfixes = ["sub_thoroughfare", "thoroughfare", "locality",
                          "sub_admin_area", "admin_area", "postal_code", "country", "full"]

site_address_checks = ["postal_code", "thoroughfare",
                       "sub_thoroughfare", "locality", "admin_area", "country"]

record_rows = []
clientele_rows = []

existing_site_locations = []

# Read the existing site locations file
if EXISTING_SITE_LOCATIONS and os.path.exists(EXISTING_SITE_LOCATIONS) and os.path.getsize(EXISTING_SITE_LOCATIONS) > 0:
    with open(EXISTING_SITE_LOCATIONS, "r") as f:
        reader = csv.DictReader(f)

        for row in reader:
            existing_site_locations.append(row)

with open(TARGET_FILE, "r") as f:
    record_reader = csv.DictReader(f)

    for row in record_reader:
        record_rows.append(row)

with open(CLIENTELE, "r") as f:
    clientele_reader = csv.DictReader(f)

    for row in clientele_reader:
        clientele_rows.append(row)

# Create a dictionary of client names and their account references
client_details = {}

for row in record_rows:
    client_name = row[CLIENT_NAME_COL].strip()
    acc_ref = row[ACC_REF_COL]
    property_type = row[PROPERTY_TYPE_COL]
    account_status = row[ACCOUNT_STATUS_COL]

    data = {
        "job_id": acc_ref,
        "property_type": property_type,
        "account_status": account_status
    }

    # Create the site address
    site_address = {}
    for postfix in site_address_postfixes:
        site_address[site_address_prefix +
                     postfix] = row[EXISTING_SITE_ADDRESS_PREFIX + postfix]

    found = False
    for existing_row in existing_site_locations:
        matches = False
        for check in site_address_checks:
            if existing_row[EXISTING_SITE_ADDRESS_PREFIX + check] == site_address[site_address_prefix + check]:
                matches = True
            else:
                matches = False
                break

        if matches and existing_row[EXISTING_CLIENT_NAME_COL] == client_name and existing_row[EXISTING_ACC_REF_COL] == acc_ref:
            # We don't need to add this to the new file
            found = True
            break

    if found:
        print(f"Skipping {client_name} - {acc_ref}")
        continue

    data = dict(data, **site_address)

    if client_name not in client_details:
        client_details[client_name] = {"jobs": [data]}
    else:
        client_details[client_name]["jobs"].append(data)

# Create find the relevant clientele ID for each client
for client in client_details:
    for row in clientele_rows:
        if row["client_name"] == client:
            client_details[client]["id"] = row[ID_COL]

# Write the site location to a file
with open("new_files\\new_site_locations.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["client", "client_name", "job_id",
                    *[site_address_prefix + f for f in site_address_postfixes], "property_type", "account_status"])

    for client in client_details:
        for job in client_details[client]["jobs"]:
            client_info = client_details[client]
            writer.writerow([client_info["id"], client, job["job_id"],
                            *[job[site_address_prefix + f] for f in site_address_postfixes], job["property_type"], job["account_status"]])
