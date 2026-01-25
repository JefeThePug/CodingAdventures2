import base64
import os
import sys
import yaml

import requests
from dotenv import load_dotenv
from flask import Flask
from psycopg2 import connect, sql
from sqlalchemy import inspect

from app.models import (
    db,
    SubEntry,
)

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__)))
path = os.path.join(parent_dir, ".env")
print(path)
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
    check_database_exists(DATABASE_URL)
    with app.app_context():
        create_missing_tables(inspect(db.engine))
        fill_permanent_data(inspect(db.engine))
    print(
        "Database setup complete. Go to the Admin dashboard (/admin) to customize for your server."
    )


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

    cursor.execute("SELECT 1 FROM pg_database WHERE datname=%s", (DATABASE_NAME,))
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
        for model in [SubEntry]:
            if model.__tablename__ not in table_names:
                model.__table__.create(db.engine)
                print(f"Table ({model.__tablename__}) created.")


def fill_permanent_data(inspector):
    """Add initial data to the tables if they're empty"""
    with app.app_context():
        table_names = inspector.get_table_names()

        if "sub_entries" in table_names:
            if not db.session.query(SubEntry).first():
                to_load = "aHR0cHM6Ly9naXN0LmdpdGh1YnVzZXJjb250ZW50LmNvbS9KZWZlVGhlUHVnL2I4N2VjOWRhMmIyNDEwZGJhMmNmNjBkZDY3ZmY5ZGU5L3Jhdy9hZHZlbnR1cmVfaHRtbC55YW1s"
                data = requests.get(base64.b64decode(to_load).decode("utf-8"))
                sub_entries = [SubEntry(**d) for d in yaml.safe_load(data.text)]
                db.session.add_all(sub_entries)
                print("Inserted html.")

        db.session.commit()


if __name__ == "__main__":
    main()
