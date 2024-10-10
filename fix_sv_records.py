import argparse
import copy
import json
import logging
import os
import typing as t

from dotenv import load_dotenv

from fulcrum_helpers.helpers import FulcrumApp, find_key_code
from fulcrum_helpers.types import App, DictValue, Record, RepeatableValue

load_dotenv()

parser = argparse.ArgumentParser(
    description="Import all the 'Other' visit types from the old JKMR app to the new SITE VISIT RECORDS app."
)
parser.add_argument(
    "--debug", help="Whether we should run in debug mode or not", action="store_true"
)
parser.add_argument(
    "--dry-run", help="Whether we should run in dry-run mode or not", action="store_true"
)
parser.add_argument(
    "--no-confirmation", help="Whether we should run without confirmation", action="store_true"
)

# Parse the arguments
args = parser.parse_args()

DEBUG = args.debug
DRY_RUN = args.dry_run
NO_CONFIRMATION = args.no_confirmation

# Logging format of: [LEVEL]::[FUNCTION]::[HH:MM:SS] - [MESSAGE]
# Where the level is colored based on the level and the rest except from the message is grey
start = "\033["
end = "\033[0m"
colors = {
    "GREEN": "32m",
    "ORANGE": "33m",
    "RED": "31m",
    "GREY": "90m",
}
for color in colors:
    # Add the start to the color
    colors[color] = start + colors[color]

logging.addLevelName(logging.DEBUG, f"{colors['GREEN']}DEBUG{colors['GREY']}")  # Green
logging.addLevelName(logging.INFO, f"{colors['GREEN']}INFO{colors['GREY']}")  # Green
logging.addLevelName(
    logging.WARNING, f"{colors['ORANGE']}WARNING{colors['GREY']}"
)  # Orange
logging.addLevelName(logging.ERROR, f"{colors['RED']}ERROR{colors['GREY']}")  # Red
logging.addLevelName(
    logging.CRITICAL, f"{colors['RED']}CRITICAL{colors['GREY']}"
)  # Red

# Define the format of the logging
logging.basicConfig(
    format=f"%(levelname)s::%(funcName)s::%(asctime)s - {end}%(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG if DEBUG else logging.INFO)

# Add a file handler to the logger
file_handler = logging.FileHandler(
    os.path.dirname(os.path.realpath(__file__)) + "/import_other_visits.log",
    mode="w+",
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(
    logging.Formatter(
        f"%(levelname)s::%(funcName)s::%(asctime)s - %(message)s", datefmt="%H:%M:%S"
    )
)
logger.addHandler(file_handler)

# Get the Fulcrum API key from the environment variables
FULCRUM_API_KEY = os.getenv("FULCRUM_API_KEY")
# Create the Fulcrum API object
FULCRUM = FulcrumApp(FULCRUM_API_KEY)


def get_product_arrays(sv_app: App, sv_records: t.List[Record]):

    sv_record_repeatable_key = find_key_code(
        sv_app["elements"], "service_visit_records"
    )
    sv_product_key = find_key_code(
        sv_app["elements"], "product_name_mapp_number_active_ingredient"
    )

    product_names = []  # type: t.List[t.List[str]]
    for record in sv_records:
        entries = record["form_values"].get(
            sv_record_repeatable_key, []
        )  # type: t.List[RepeatableValue]
        for entry in entries:
            product_name = entry.get("form_values", {}).get(
                sv_product_key
            )  # type: t.Union[DictValue, None]

            if product_name is None:
                continue

            product_names.append(product_name["choice_values"])
            product_names.append(product_name["other_values"])

    # Compare inner arrays and de-duplicate entries that have the same products in the same order
    product_names = list(set([tuple(names) for names in product_names]))

    logger.debug(f"Product names: {json.dumps(product_names, indent=2)}")

    return product_names


CORRECT_NAMES = {
    "RoundUp Pro-Vantage 480, 15534, Glyphosate": [
        ["RoundUp Pro-Vantage 480", " 15534", " Glyphosate"],
        ["RoundUp Pro-Vantage 480", " 15534", " Glyphosate", " 480 ml/L"],
        ["RoundUp Pro-Vantage 480", " 15534", " Glyhosate"],
    ],
    "Roundup Pro-Biactive, 10330, Glyphosate": [
        ["Roundup Pro-Biactive", " 10330", " Glyphosate"]
    ],
    "Roundup Pro-Bio, 15539, Glyphosate": [
        ["Roundup Pro-Bio", " 15539", " Glyphosate"]
    ],
    "Synero, 14708, aminopyralid 30 g/L": [],
    "Fluroxypyr 100 g/L": [],
    "Kaskara, 15593, 200g/l 2,4-D, 85g/l dicamba and 65g/l triclopyr.": [],
    "Kurtail Evo, 19020, 160 g/l 2,4-D and 240 g/l glyphosate.": [
        ["Kurtail Evo", " 19020", " 160 g/l 2", "4-D and 240 g/l glyphosate."]
    ],
    "Diamond, 18832, 160 g/l 2,4-D and 240 g/l glyphosate.": [],
    "Depitox, 17597, 500g/l 2,4-D": [["Depitox", " 17597", " 500g/l 2", "4-D"]],
    "Ecoplug Max, 17581, 720g/kg glyphosate (283 mg plug) (203.76 mg/plug dose)": [],
}


def get_corrected_product_names(product_arrays: t.List[t.List[str]]):
    CORRECT_NAMES_TUPLE = {
        tuple(array): name for name, arrays in CORRECT_NAMES.items() for array in arrays
    }

    correct_names = {}  # type: t.Dict[t.Tuple[str], str]

    for array in product_arrays:
        if len(product_arrays) == 1 and product_arrays[0] in CORRECT_NAMES:
            return {product_arrays[0]: CORRECT_NAMES[product_arrays[0]]}

        tuple_array = tuple(array)
        if tuple_array in CORRECT_NAMES_TUPLE:
            correct_names[tuple_array] = CORRECT_NAMES_TUPLE[tuple_array]

    logger.debug(
        f"Corrected product names: {json.dumps({str(k): v for k, v in correct_names.items()}, indent=2)}"
    )

    return correct_names

def confirm_or_fail(message: str):
    confirmations = ["y", "yes"]

    user_input = ""
    if not DRY_RUN:
        user_input = input(f"{message}.\nContinue? (y/n): ")
    else:
        logger.info(message)

    if user_input.lower() not in confirmations and not DRY_RUN:
        raise Exception("User aborted script.")

    logger.info("Continuing as requested...")


def update_product_names(
    sv_app: App,
    sv_records: t.List[Record],
    corrected_product_names: t.Dict[t.Tuple[str], str],
):
    sv_record_repeatable_key = find_key_code(
        sv_app["elements"], "service_visit_records"
    )
    sv_product_key = find_key_code(
        sv_app["elements"], "product_name_mapp_number_active_ingredient"
    )

    record_update_count = 0

    for record in sv_records:
        skip_reason = None  # type: t.Optional[str]
        entries = record["form_values"].get(sv_record_repeatable_key, [])
        record_before = copy.deepcopy(record)

        if len(entries) == 0:
            skip_reason = "No service visit records"
            continue

        for entry in entries:
            product_name = entry.get("form_values", {}).get(
                sv_product_key
            )  # type: t.Union[DictValue, None]

            if product_name is None:
                continue

            choice_values_tuple = tuple(product_name["choice_values"])
            other_values_tuple = tuple(product_name["other_values"])

            if not (
                choice_values_tuple in corrected_product_names
                or other_values_tuple in corrected_product_names
            ):
                skip_reason = "No product names need correcting"
                continue

            new_choice_values = list(filter(lambda x: x, [corrected_product_names.get(choice_values_tuple, None)]))
            new_other_values = list(filter(lambda x: x, [corrected_product_names.get(other_values_tuple, None)]))

            logger.debug(
                f"Old product choice name: {product_name["choice_values"]}, New product name: {new_choice_values}"
            )
            logger.debug(
                f"Old product other name: {product_name["other_values"]}, New product name: {new_other_values}"
            )

            if len(new_choice_values):
                product_name["choice_values"] = new_choice_values

            if len(new_other_values):
                product_name["other_values"] = new_other_values

        if skip_reason:
            logger.debug(f"Skipping record {record['id']}: {skip_reason}")
            continue

        record_update_count += 1

        if not DRY_RUN:
            if not NO_CONFIRMATION:
                confirm_or_fail(f"Updating record {record['id']}")
            FULCRUM.update_fulcrum_record(record["id"], record)

    logger.debug(f"Updated records: {record_update_count}")


def main():
    sv_app = FULCRUM.get_app("SITE VISIT RECORDS")
    sv_records = FULCRUM.get_app_records(sv_app)

    sv_product_arrays = get_product_arrays(sv_app, sv_records)
    sv_corrected_product_names = get_corrected_product_names(sv_product_arrays)

    update_product_names(sv_app, sv_records, sv_corrected_product_names)


if __name__ == "__main__":
    main()
