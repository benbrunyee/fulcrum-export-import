import argparse
import json
import os

from dotenv import load_dotenv
from fulcrum import Fulcrum

load_dotenv()

parser = argparse.ArgumentParser(description="Get a record from Fulcrum.")
parser.add_argument("--record_id", "-i", help="The ID of the record you want to get.")

args = parser.parse_args()


# Constants

RECORD_ID = args.record_id
FULCRUM_API_KEY = os.getenv("FULCRUM_API_KEY")

FULCRUM = Fulcrum(FULCRUM_API_KEY)


def main():
    record = FULCRUM.records.find(RECORD_ID)

    print(json.dumps(record, indent=4, sort_keys=True))
    # Write the record to a temporary file
    with open(".record.json", "w") as outfile:
        json.dump(record, outfile, indent=2, sort_keys=True)
    print("Record written to .record.json")


if __name__ == "__main__":
    main()
