import base64
import os
from pathlib import Path

import requests
import yaml
from dotenv import load_dotenv
from flask import Flask
from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import SQLAlchemyError

from app.models import (
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

@event.listens_for(db.metadata, 'after_create')
def receive_after_create(target, connection, tables, **kwargs):
    for table in tables:
        print(f"Table created: {table.name}")


def main():
    check_database_exists()
    create_missing_tables()
    fill_permanent_data()
    print(
        "Database setup complete. Go to the Admin dashboard (/admin) to customize for your server."
    )


def check_database_exists():
    """Create database in PostgreSQL if it doesn't exist"""
    engine = create_engine(ADMIN_URL).execution_options(isolation_level="AUTOCOMMIT")

    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :dbname"),
            {"dbname": DATABASE_NAME}
        )
        if not result.fetchone():
            # In SQLAlchemy, identifiers for CREATE DATABASE must be raw strings
            conn.execute(text(f'CREATE DATABASE "{DATABASE_NAME}"'))
            print(f"Database {DATABASE_NAME} created.")


def create_missing_tables(inspector):
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


def fill_permanent_data(inspector):
    """Add initial data to the tables if they're empty"""
    with app.app_context():
        table_names = inspector.get_table_names()

        if "sub_entries" in table_names:
            if not db.session.query(SubEntry).first():
                to_load = "aHR0cHM6Ly9naXN0LmdpdGh1YnVzZXJjb250ZW50LmNvbS9KZWZlVGhlUHVnL2I4N2VjOWRhMmIyNDEwZGJhMmNmNjBkZDY3ZmY5ZGU5L3Jhdy9hZHZlbnR1cmVfaHRtbC55YW1s"
                try:
                    response = requests.get(base64.b64decode(to_load).decode("utf-8"), timeout=10)
                    response.raise_for_status()
                    data = yaml.safe_load(response.text)
                    sub_entries = [SubEntry(**d) for d in data]
                    db.session.add_all(sub_entries)
                    print("Inserted HTML.")
                except SQLAlchemyError as e:
                    print(f"Failed to seed HTML data: {e}")

        db.session.commit()


if __name__ == "__main__":
    main()
