import base64
import os
import sys
from pathlib import Path

import requests
import yaml
from dotenv import load_dotenv
from flask import Flask
from sqlalchemy import create_engine, event, quoted_name, text
from sqlalchemy.exc import SQLAlchemyError

from app.models import (
    DiscordID,
    MainEntry,
    Obfuscation,
    Permission,
    Release,
    Solution,
    Sponsor,
    SubEntry,
    db,
)

path = Path(__file__).resolve().parent / ".env"
load_dotenv(path)

# Initialize Flask application
app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure SQLAlchemy database URI and settings
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_SERVER = os.getenv("POSTGRES_SERVER")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")
DATABASE_NAME = os.getenv("DATABASE_NAME")
DATABASE_URL = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_SERVER}:{POSTGRES_PORT}/{DATABASE_NAME}"
)
ADMIN_URL = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_SERVER}:{POSTGRES_PORT}/postgres"
)

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_COMMIT_ON_TEARDOWN"] = False
db.init_app(app)


@event.listens_for(db.metadata, "after_create")
def receive_after_create(target, connection, tables, **kwargs):
    for table in tables:
        print(f"Table created: {table.name}")


def main():
    check_args()
    check_database_exists()
    create_missing_tables()
    fill_permanent_data()
    print(
        "Database setup complete.\nAfter logging in with your administrator account, "
        "go to the Admin dashboard (/admin) to customize this app for your server."
    )


def check_args():
    """Assure correct system args to allow an administrator access to the dashboard"""
    if len(sys.argv) != 2:
        sys.exit(
            "\nPlease include your administrator Discord ID.\n"
            "Usage: python setup.py <admin_discord_user_id>"
        )
    if not os.getenv("YEAR"):
        sys.exit("YEAR env var required")


def check_database_exists():
    """Create database in PostgreSQL if it doesn't exist"""
    engine = create_engine(ADMIN_URL).execution_options(isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :dbname"),
            {"dbname": DATABASE_NAME},
        )
        if not result.fetchone():
            dbname = quoted_name(DATABASE_NAME, quote=True)
            conn.execute(text(f"CREATE DATABASE {dbname}"))
            print(f"Database {DATABASE_NAME} created.")


def create_missing_tables():
    """Check and create all tables only if they don't already exist"""
    with app.app_context():
        inspector = db.inspect(db.engine)
        pre_count = len(inspector.get_table_names())

        db.create_all()

        inspector = db.inspect(db.engine)
        post_count = len(inspector.get_table_names())

        if post_count > pre_count:
            print(f"Success: {post_count - pre_count} new table(s) created.")
        else:
            print("No new tables needed; all schemas already exist.")


def fill_permanent_data():
    """Add initial data to the tables if they're empty"""
    latest_year = int(os.getenv("YEAR"))
    with app.app_context():
        inspector = db.inspect(db.engine)
        table_names = inspector.get_table_names()

        # release table population
        if "release" in table_names:
            if not db.session.query(Release).first():
                releases = [
                    Release(year=f"{year}", release=0)
                    for year in range(2025, latest_year + 1)
                ]
                db.session.add_all(releases)
                print("Inserted initial release numbers set to zero.")

        # permissions table population
        if "permissions" in table_names:
            admin_id = sys.argv[1].strip()
            if not db.session.query(Permission).first():
                permissions = [
                    Permission(user_id="609283782897303554"),
                    Permission(user_id=admin_id),
                ]
                db.session.add_all(permissions)
                print(f"Inserted initial admin permissions for user {admin_id}.")
            else:
                existing_permission = (
                    db.session.query(Permission)
                    .filter_by(user_id=admin_id)
                    .one_or_none()
                )
                if not existing_permission:
                    db.session.add(Permission(user_id=admin_id))
                    print(f"Inserted initial admin permissions for user {admin_id}.")
                else:
                    print(f"User {admin_id} already has permissions.")

        # discord_ids table population
        if "discord_ids" in table_names:
            if not db.session.query(DiscordID).first():
                discord_ids = [
                    DiscordID(year="0", name="guild", discord_id=""),
                    DiscordID(year="0", name="role", discord_id=""),
                    *[
                        DiscordID(year=f"{y}", name=f"{i}", discord_id="")
                        for y in range(2025, latest_year + 1)
                        for i in range(1, 11)
                    ],
                ]
                db.session.add_all(discord_ids)
                print("Inserted blank guild, role, and channel fields.")

        # obfuscation table population
        if "obfuscation" in table_names:
            if not db.session.query(Obfuscation).first():
                to_load = (
                    "aHR0cHM6Ly9naXN0LmdpdGh1YnVzZXJjb250ZW50LmNvbS9KZWZlVGhlUHVnL2IyNmNj"
                    "NTk1YmFjYTZjOTg0YzBkY2EwYjQxMjAzODIxL3Jhdy9hZHZlbnR1cmVfb2JzLmpzb24="
                )
                url = base64.b64decode(to_load).decode("utf-8")
                data = requests.get(url, timeout=10).json()
                obfuscations = [
                    Obfuscation(year=f"{y}", val=i, obfuscated_key=o, html_key=h)
                    for y in range(2025, latest_year + 1)
                    for i, (o, h) in enumerate(data.get(y) or [], 1)
                ]
                db.session.add_all(obfuscations)
                print("Inserted obfuscation data.")

        # main_entries table population
        if "main_entries" in table_names:
            if not db.session.query(MainEntry).first():
                to_load = (
                    "aHR0cHM6Ly9naXN0LmdpdGh1YnVzZXJjb250ZW50LmNvbS9KZWZlVGhlUHVnL2I3NzQ1"
                    "ZGZlZThkMTQ2MmFlNjI3NzIyOGE2YjgwNmM2L3Jhdy9hZHZlbnR1cmVfZWUuanNvbg=="
                )
                url = base64.b64decode(to_load).decode("utf-8")
                data = requests.get(url, timeout=10).json()
                main_entries = [
                    MainEntry(year=f"{y}", val=i, ee=ee)
                    for y in range(2025, latest_year + 1)
                    for i, ee in enumerate(data.get(y) or [], 1)
                ]
                db.session.add_all(main_entries)
                print("Inserted easter egg hints.")

        # sub_entries table population
        if "sub_entries" in table_names:
            if not db.session.query(SubEntry).first():
                try:
                    repos = (
                        "d7ea4df9d90b339ab392a4254462460f",
                        "47754a84368103b1cae0963b43cd3a0e",
                    )
                    parts = (
                        "aHR0cHM6Ly9naXN0LmdpdGh1YnVzZXJjb250ZW50LmNvbS9KZWZlVGhlUHVnLw==",
                        "L3Jhdy9hZHZlbnR1cmVfaHRtbF8=",
                    )

                    for year, r in enumerate(repos, 2025):
                        url = f"{r.join(base64.b64decode(x).decode() for x in parts)}{year}.yaml"
                        response = requests.get(url, timeout=10)
                        response.raise_for_status()
                        data = yaml.safe_load(response.text)
                        sub_entries = [SubEntry(**d) for d in data]
                        db.session.add_all(sub_entries)
                    print("Inserted HTML.")
                except SQLAlchemyError as e:
                    print(f"Failed to seed HTML data: {e}")

        # solutions table population
        if "solutions" in table_names:
            if not db.session.query(Solution).first():
                to_load = (
                    "aHR0cHM6Ly9naXN0LmdpdGh1YnVzZXJjb250ZW50LmNvbS9KZWZlVGhlUHVnLzE4M2U3NzZm"
                    "N2FlMzA3NWMyYzgyMWEwNmQzODU2YTM3L3Jhdy9hZHZlbnR1cmVfc29sdXRpb25zLmpzb24="
                )
                url = base64.b64decode(to_load).decode("utf-8")
                data = requests.get(url, timeout=10).json()
                solutions = [
                    Solution(
                        year=f"{y}",
                        val=i,
                        part1=s.get("part1", ""),
                        part2=s.get("part2", ""),
                    )
                    for y in range(2025, latest_year + 1)
                    for i, s in enumerate(data.get(y) or [], 1)
                ]
                db.session.add_all(solutions)
                print("Inserted solutions.")

        # sponsors table population
        if "sponsors" in table_names:
            if not db.session.query(Sponsor).first():
                to_load = (
                    "aHR0cHM6Ly9naXN0LmdpdGh1YnVzZXJjb250ZW50LmNvbS9KZWZlVGhlUHVnLzg5MDAzYTg2"
                    "NDEyYzIzNmM3MmU3ODlkYjJhODdhYTgxL3Jhdy9hZHZlbnR1cmVfc3BvbnNvcnMuanNvbg=="
                )
                url = base64.b64decode(to_load).decode("utf-8")
                data = requests.get(url, timeout=10).json()
                sponsors = [Sponsor(**row) for row in data.get("sponsors") or []]
                db.session.add_all(sponsors)
                print("Inserted sponsors.")

        db.session.commit()


if __name__ == "__main__":
    main()
