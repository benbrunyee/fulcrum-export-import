import os

from dotenv import load_dotenv
from fulcrum import Fulcrum
from tabulate import tabulate

load_dotenv()

FULCRUM_API_KEY = os.getenv("FULCRUM_API_KEY")
FULCRUM = Fulcrum(FULCRUM_API_KEY)


def main():
    memberships = FULCRUM.memberships.search()["memberships"]

    rows = [
        [
            m.get("user_id"),
            m.get("first_name"),
            m.get("last_name"),
            m.get("email"),
            m.get("role_name"),
        ]
        for m in sorted(
            memberships, key=lambda m: m.get("first_name", "") + m.get("last_name", "")
        )
    ]

    print(
        tabulate(
            rows,
            headers=["User ID", "First Name", "Last Name", "Email", "Role"],
            tablefmt="simple",
        )
    )
    print(f"\n{len(rows)} user(s) found.")


if __name__ == "__main__":
    main()
