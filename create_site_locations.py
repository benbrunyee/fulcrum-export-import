import csv
import os

if not os.path.exists("new_files"):
    os.makedirs("new_files")

CLIENTELE = "bb_clientele_import\\bb_clientele_import.csv"
RECORDS = "knotweed_survey_and_management_plan\\knotweed_survey_and_management_plan.csv"

id_col = "fulcrum_id"
client_col = "client_name"
acc_ref_col = "account_reference"
property_type_col = "property_type"
account_status_col = "account_status"

site_address_prefix = "site_address_"
site_address_postfixes = ["sub_thoroughfare", "thoroughfare", "locality",
                          "sub_admin_area", "admin_area", "postal_code", "country", "full"]

record_rows = []
clientele_rows = []

with open(RECORDS, "r") as f:
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
    client_name = row[client_col]
    acc_ref = row[acc_ref_col]
    property_type = row[property_type_col]
    account_status = row[account_status_col]

    data = {
        "job_id": acc_ref,
        "property_type": property_type,
        "account_status": account_status
    }

    # Create the site address
    site_address = {}
    for postfix in site_address_postfixes:
        site_address[site_address_prefix +
                     postfix] = row[site_address_prefix + postfix]

    data = dict(data, **site_address)

    if client_name not in client_details:
        client_details[client_name] = {"jobs": [data]}
    else:
        client_details[client_name]["jobs"].append(data)

# Create find the relevant clientele ID for each client
for client in client_details:
    for row in clientele_rows:
        if row[client_col] == client:
            client_details[client]["id"] = row[id_col]

# Write the site location to a file
with open("new_files\\site_locations.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["client", "client_name", "job_id",
                    *[site_address_prefix + f for f in site_address_postfixes], "property_type", "account_status"])

    for client in client_details:
        for job in client_details[client]["jobs"]:
            writer.writerow([client_details[client]["id"], client, job["job_id"],
                            *[job[site_address_prefix + f] for f in site_address_postfixes], job["property_type"], job["account_status"]])
