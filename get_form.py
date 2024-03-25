import argparse
import json
import os

from dotenv import load_dotenv
from fulcrum import Fulcrum

load_dotenv()

parser = argparse.ArgumentParser(description="Get a form from Fulcrum.")
parser.add_argument("--form_name", "-n", help="The name of the form to get data from.")

args = parser.parse_args()


# Constants

FORM_NAME = args.form_name
FULCRUM_API_KEY = os.getenv("FULCRUM_API_KEY")

FULCRUM = Fulcrum(FULCRUM_API_KEY)


def main():
    target_form = None

    forms = FULCRUM.forms.search()

    for form in forms["forms"]:
        if form["name"] == FORM_NAME:
            target_form = form
            break

    if not target_form:
        print("Form not found")
        return

    print(json.dumps(target_form, indent=4, sort_keys=True))

    # Write the form to a temporary file
    with open(".form.json", "w") as outfile:
        json.dump(target_form, outfile, indent=2, sort_keys=True)
    print("Form written to .form.json")


if __name__ == "__main__":
    main()
