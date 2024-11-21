import logging
import time
import typing as t

import requests
from fulcrum import Fulcrum

from .types import App, AppElement, AppElementTypes, Record

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


def rate_limited(max_per_second):
    """
    Decorator to limit the rate of function calls.
    """
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


class FulcrumApp:
    fulcrum: Fulcrum
    api_key: str

    def __init__(self, api_key: str):
        self.fulcrum = Fulcrum(api_key)
        self.api_key = api_key

    def list_apps(self) -> t.List[App]:
        """
        List all the apps in the Fulcrum account
        """
        apps = self.fulcrum.forms.search()["forms"]
        logger.debug(f"Found {len(apps)} apps")
        return apps

    def get_app(self, name: str) -> App:
        """
        Get an app by name
        """
        logger.info(f"Getting app: {name}")
        apps = self.list_apps()
        for app in apps:
            if app["name"] == name:
                return app  # type: App

    def get_app_records(self, app: App) -> t.List[Record]:
        """
        Get the records of a specific app
        """
        records = self.fulcrum.records.search({"form_id": app["id"]})["records"]
        return records

    # Rate limited for 4000 calls per hour (actual limit is 5000/h but we want to be safe)
    @rate_limited(4000 / 3600)
    def update_fulcrum_record(self, record_id: str, record: Record):
        """
        Update a record in Fulcrum
        """

        # Update the record
        updated_record = self.fulcrum.records.update(record_id, {"record": record})

        if "errors" in updated_record["record"]:
            logger.error(f"Error updating record")
            logger.error(updated_record)
            exit(1)

        logger.info(f"Updated record: {updated_record['record']['id']} with new entry")

    @rate_limited(4000 / 3600)
    def get_record_attachments(self, record_id: str):
        """
        Get the attachments of a record in Fulcrum
        """
        resp = requests.get(
            "https://api.fulcrumapp.com/api/v2/attachments",
            params={"record_id": record_id},
            headers={"X-ApiToken": self.api_key, "Accept": "application/json"},
        )

        if resp.status_code != 200:
            logger.error(resp)
            raise Exception(f"Failed to get attachments for record {record_id}")

        resp_json = resp.json()

        return resp_json

    @rate_limited(4000 / 3600)
    def get_attachment(self, attachment_id: str):
        """
        Get an attachment from Fulcrum
        """
        resp = requests.get(
            f"https://api.fulcrumapp.com/api/v2/attachments/{attachment_id}",
            headers={"X-ApiToken": self.api_key, "Accept": "application/json"},
        )

        if resp.status_code != 200:
            logger.error(resp)
            raise Exception(f"Failed to get attachment {attachment_id}")

        resp_json = resp.json()

        return resp_json

    def list_attachments(self):
        """
        List all the attachments in the Fulcrum account
        """
        resp = requests.get(
            "https://api.fulcrumapp.com/api/v2/attachments?form_id=8b47f113-c60f-4016-af20-1a4367887eba",
            headers={"X-ApiToken": self.api_key, "Accept": "application/json"},
        )

        if resp.status_code != 200:
            logger.error(resp)
            raise Exception("Failed to get attachments")

        resp_json = resp.json()

        return resp_json


def find_key_code(elements: t.List[AppElement], data_name: str) -> str | None:
    """
    Recursively search an app's elements to find the key
    code of a field in an app
    """
    section_types = [
        "Section",
        "Repeatable",
    ]  # type: AppElementTypes

    for element in elements:
        if element["data_name"] == data_name:
            return element["key"]

        if element["type"] in section_types:
            key_code = find_key_code(element["elements"], data_name)
            if key_code:
                return key_code

    return None
