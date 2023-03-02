import csv
import os

if not os.path.exists("new_files"):
    os.makedirs("new_files")

FILE = "knotweed_survey_and_management_plan\\knotweed_survey_and_management_plan.csv"

reader = None

id_col = "fulcrum_id"
client_col = "client_name"
acc_ref_col = "account_reference"

client_names = []
acc_refs = []

client_details = {}

# Read the file using csv
with open(FILE, 'r') as f:
    reader = csv.DictReader(f)

    for row in reader:
        # Find account reference and client name
        # Highlight duplicates
        if row[client_col] not in client_names:
            client_names.append(row[client_col])
        else:
            print(
                f"ID: {row[id_col]}, Duplicate client name: {row[client_col]}, Account reference: {row[acc_ref_col]}")

        if row[acc_ref_col] not in acc_refs:
            acc_refs.append(row[acc_ref_col])
        else:
            print(
                f"ID: {row[id_col]}, Duplicate account reference: {row[acc_ref_col]}, Client: {row[client_col]}")

        if row[client_col] not in client_details:
            client_details[row[client_col]] = [row[acc_ref_col]]
        else:
            client_details[row[client_col]].append(row[acc_ref_col])

# Print the client details
for client in client_details:
    print(f"Client: {client}, Account references: {client_details[client]}")

# Write the client names to a file, generate a unique id for each client
with open("new_files\\client_names.csv", 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["client_name"])
    for client in client_names:
        writer.writerow([client])
