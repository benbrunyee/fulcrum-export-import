import argparse
import os
import time

from dotenv import load_dotenv
from fulcrum import Fulcrum
from tqdm import tqdm

load_dotenv()

parser = argparse.ArgumentParser(
    description="Update the 'assigned_to_id' field on all records in a Fulcrum app."
)
parser.add_argument(
    "--app_id", "-a", required=True, help="The ID of the app to update records for."
)
parser.add_argument(
    "--email",
    "-e",
    required=True,
    help="Email address of the user to assign records to.",
)
parser.add_argument(
    "--dry_run",
    "-d",
    action="store_true",
    help="Preview changes without applying them.",
)

args = parser.parse_args()

FULCRUM_API_KEY = os.getenv("FULCRUM_API_KEY")
FULCRUM = Fulcrum(FULCRUM_API_KEY)

APP_ID = args.app_id
EMAIL = args.email.strip().lower()
DRY_RUN = args.dry_run


def get_user_by_email(email: str) -> tuple[str, str]:
    memberships = FULCRUM.memberships.search()["memberships"]

    for membership in memberships:
        if membership.get("email", "").strip().lower() == email:
            first_name = membership.get("first_name", "").strip()
            last_name = membership.get("last_name", "").strip()
            user_name = " ".join(part for part in (first_name, last_name) if part)
            return membership["user_id"], user_name

    print(f"Could not find user with email: {email}")
    exit(1)


USER_ID, USER_NAME = get_user_by_email(EMAIL)
print(f"Assigning records to {USER_NAME} ({USER_ID}, {EMAIL})\n")


def rate_limited(max_per_second):
    minimum_interval = 1.0 / float(max_per_second)

    def decorate(func):
        last_time_called = [0.0]

        def rate_limited_function(*args, **kargs):
            elapsed = time.perf_counter() - last_time_called[0]
            left_to_wait = minimum_interval - elapsed
            if left_to_wait > 0:
                time.sleep(left_to_wait)
            ret = func(*args, **kargs)
            last_time_called[0] = time.perf_counter()
            return ret

        return rate_limited_function

    return decorate


def update_record(record_id: str, record: dict):
    if DRY_RUN:
        return False

    updated = FULCRUM.records.update(record_id, {"record": record})

    if "errors" in updated.get("record", {}):
        print(f"Error updating record {record_id}: {updated['record']['errors']}")
        exit(1)

    return True


def main():
    if DRY_RUN:
        print("[DRY RUN] No changes will be made.\n")

    records = FULCRUM.records.search(url_params={"form_id": APP_ID})["records"]
    print(f"Found {len(records)} records in app {APP_ID}")

    records_to_update = [r for r in records if r.get("assigned_to_id") != USER_ID]
    already_assigned_count = len(records) - len(records_to_update)

    if already_assigned_count:
        print(
            f"Skipping {already_assigned_count} record(s) already assigned to user {USER_ID}"
        )

    if not records_to_update:
        print("No records require updating.")
        return

    progress_bar = tqdm(
        records_to_update, total=len(records_to_update), desc="Updating records"
    )

    updated_count = 0
    for record in progress_bar:
        record["assigned_to_id"] = USER_ID
        record["assigned_to"] = USER_NAME

        was_updated = update_record(record["id"], record)

        if was_updated:
            updated_count += 1
            progress_bar.set_description(f"Updated record: {record['id']}")
        elif DRY_RUN:
            updated_count += 1
            progress_bar.set_description(f"Would update record: {record['id']}")

    progress_bar.close()

    if DRY_RUN:
        print(f"\n[DRY RUN] Would have updated {updated_count} record(s).")
    else:
        print(f"\nFinished. Updated {updated_count} record(s).")


if __name__ == "__main__":
    main()
