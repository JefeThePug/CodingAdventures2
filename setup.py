import base64
import os
import sys
import yaml

import requests
from dotenv import load_dotenv
from flask import Flask
from psycopg2 import connect, sql
from sqlalchemy import inspect

from models import (
    db,
    DiscordID,
    MainEntry,
    SubEntry,
    Obfuscation,
    Progress,
    Solution,
    Permissions,
    Release,
)

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
path = os.path.join(parent_dir, ".env")
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

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_COMMIT_ON_TEARDOWN"] = False

db.init_app(app)


def main():
    # check_args()
    check_database_exists(DATABASE_URL)
    with app.app_context():
        create_missing_tables(inspect(db.engine))
        fill_permanent_data(inspect(db.engine))
    print(
        "Database setup complete. Go to the Admin dashboard (/admin) to customize for your server."
    )


def check_args():
    if len(sys.argv) != 2:
        sys.exit("\nUsage: python setup.py <admin_discord_user_id>")


def check_database_exists(database_url):
    """Create database in PostgreSQL if it doesn't exist"""
    connection = connect(
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        host=POSTGRES_SERVER,
        port=POSTGRES_PORT,
        dbname="postgres",
    )
    connection.autocommit = True
    cursor = connection.cursor()

    cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = %s", (DATABASE_NAME,))
    if cursor.fetchone() is None:
        cursor.execute(
            sql.SQL("CREATE DATABASE {}").format(sql.Identifier(DATABASE_NAME))
        )
        print(f"Database {DATABASE_NAME} created.")
    cursor.close()
    connection.close()


def create_missing_tables(inspector):
    """Check and create all tables only if they don't already exist"""
    with app.app_context():
        table_names = inspector.get_table_names()
        for model in [
            #DiscordID,
            MainEntry,
            SubEntry,
            #Obfuscation,
            #Progress,
            #Solution,
            #Permissions,
            #Release,
        ]:
            if model.__tablename__ not in table_names:
                model.__table__.create(db.engine)
                print(f"Table ({model.__tablename__}) created.")


def fill_permanent_data(inspector):
    """Add initial data to the tables if they're empty"""
    with app.app_context():
        table_names = inspector.get_table_names()
        # if "discord_ids" in table_names:
        #     if not db.session.query(DiscordID).first():
        #         discord_ids = [DiscordID(year="0", name="guild", discord_id="")]
        #         discord_ids += [DiscordID(year=y, name=f"{i}", discord_id="") for y in ("2025", "2026")
        #                         for i in range(1, 11)]
        #         db.session.add_all(discord_ids)
        #         print("Inserted blank channel fields.")

        # if "release" in table_names:
        #     if not db.session.query(Release).first():
        #         releases = [Release(year="2025", release=10), Release(year="2026", release=0)]
        #         db.session.add_all(releases)
        #         print("Inserted initial release number.")

        # if "permissions" in table_names:
        #     if not db.session.query(Permissions).first():
        #         # If the table is blank
        #         permissions = [Permissions(user_id="609283782897303554"), Permissions(user_id=sys.argv[1].strip())]
        #         db.session.add_all(permissions)
        #         print("Inserted initial admin permissions.")
        #     else:
        #         # Check if sys.argv[1] is already in the Permissions table
        #         existing_permission = db.session.query(Permissions).filter_by(user_id=sys.argv[1].strip()).first()
        #         if not existing_permission:
        #             db.session.add(Permissions(user_id=sys.argv[1].strip()))
        #             print(f"Inserted permission for user {sys.argv[1].strip()}.")
        #         else:
        #             print(f"User {sys.argv[1].strip()} already has permissions.")

        # if "obfuscation" in table_names:
        #     if not db.session.query(Obfuscation).first():
        #         to_load = "aHR0cHM6Ly9naXN0LmdpdGh1YnVzZXJjb250ZW50LmNvbS9KZWZlVGhlUHVnL2IyNmNjNTk1YmFjYTZjOTg0YzBkY2EwYjQxMjAzODIxL3Jhdy9hZHZlbnR1cmVfb2JzLmpzb24="
        #         data = requests.get(base64.b64decode(to_load).decode('utf-8')).json()
        #         obfuscations = [Obfuscation(year=y, val=i, obfuscated_key=o, html_key=h) for y in ("2025", "2026")
        #                         for i, (o, h) in enumerate(data.get(y, []), 1)]
        #         db.session.add_all(obfuscations)
        #         print("Inserted obfuscation data.")

        # if "main_entries" in table_names:
        #     if not db.session.query(MainEntry).first():
        #         to_load = "aHR0cHM6Ly9naXN0LmdpdGh1YnVzZXJjb250ZW50LmNvbS9KZWZlVGhlUHVnL2I3NzQ1ZGZlZThkMTQ2MmFlNjI3NzIyOGE2YjgwNmM2L3Jhdy9hZHZlbnR1cmVfZWUuanNvbg=="
        #         data = requests.get(base64.b64decode(to_load).decode('utf-8')).json()
        #         main_entries = [MainEntry(year=y, val=i, ee=ee) for y in ("2025", "2026")
        #                         for i, ee in enumerate(data.get(y, []), 1)]
        #         db.session.add_all(main_entries)
        #         print("Inserted easter egg hints.")

        if "sub_entries" in table_names:
            if not db.session.query(SubEntry).first():
                to_load = "aHR0cHM6Ly9naXN0LmdpdGh1YnVzZXJjb250ZW50LmNvbS9KZWZlVGhlUHVnL2I4N2VjOWRhMmIyNDEwZGJhMmNmNjBkZDY3ZmY5ZGU5L3Jhdy9hZHZlbnR1cmVfaHRtbC55YW1s"
                data = requests.get(base64.b64decode(to_load).decode('utf-8'))
                sub_entries = [SubEntry(**d) for d in yaml.safe_load(data.text)]
                db.session.add_all(sub_entries)
                print("Inserted html.")

        # if "solutions" in table_names:
        #     if not db.session.query(Solution).first():
        #         to_load = "aHR0cHM6Ly9naXN0LmdpdGh1YnVzZXJjb250ZW50LmNvbS9KZWZlVGhlUHVnLzE4M2U3NzZmN2FlMzA3NWMyYzgyMWEwNmQzODU2YTM3L3Jhdy9hZHZlbnR1cmVfc29sdXRpb25zLmpzb24="
        #         data = requests.get(base64.b64decode(to_load).decode('utf-8')).json()
        #         solutions = [Solution(year=y, val=i, part1=s.get("part1", ""), part2=s.get("part2", ""))
        #                      for y in ("2025", "2026") for i, s in enumerate(data.get(y, []), 1)]
        #         db.session.add_all(solutions)
        #         print("Inserted solutions.")

        db.session.commit()


if __name__ == "__main__":
    main()
