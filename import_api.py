import argparse
import os

from dotenv import load_dotenv
from fulcrum import Fulcrum

parser = argparse.ArgumentParser(
    description='Import data from a CSV file into Fulcrum.')
parser.add_argument(
    '--form_name', "-n", help='The name of the form to import data into.')

args = parser.parse_args()

load_dotenv()

FULCRUM_API_KEY = os.getenv('FULCRUM_API_KEY')

fulcrum = Fulcrum(FULCRUM_API_KEY)

forms = fulcrum.forms.search(args.form_name)

target_form = None

for form in forms["forms"]:
    if form["name"] == args.form_name:
        target_form = form
        break

if target_form is None:
    print("Form not found.")
    exit()
