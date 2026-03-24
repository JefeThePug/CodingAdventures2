# Practical Python Coding Adventure v2

**Live at:** [https://adventure.practicalpython.org](https://adventure.practicalpython.org)

Version 2 of **Coding Adventure** brings a fully modular backend, a redesigned user experience, and flexible setup options for new or returning users. The project remains a series of interactive coding challenges (each with two parts), inspired by [Advent of Code](https://adventofcode.com), built for the Practical Python Discord community. Currently there are two collections of puzzles, intended to be released one collection per year.

All previous features have been preserved and improved, with better code structure, usability, and deployment options.

---

## Key Updates in Version 2

- **Modular Backend** – Blueprints, services, and templating now separate concerns for clean, maintainable code.
- **Updated Database** – New PostgreSQL schema for version 2 challenges, with optional migration from version 1.
- **Flexible Setup Options** – Start fresh or carry over progress from version 1 using `SETUP_TYPE`.
- **Redesigned UX** – Clearer layout, updated challenge pages, and better progress feedback.
- **Challenge Organization** – Puzzle inputs and media now structured for multiple years, simplifying future expansion.
- **Improved Admin Dashboard** – Modular routes and updated UI for managing users, challenges, and releases.

---

## Tech Stack

- Python 3.10+
- Flask (modular blueprint architecture)
- PostgreSQL
- SQLAlchemy ORM
- Docker / Docker Compose
- uv for dependency management
- Discord OAuth2 integration

---

## Getting Started

### Prerequisites

- Python 3.10+
- Docker & Docker Compose
- PostgreSQL (local or Docker-based)

---

### Environment Variables

Create a `.env` file in the project root with the following variables:

```ini
# PostgreSQL
POSTGRES_USER="postgres"
POSTGRES_PASSWORD="postgres"
POSTGRES_SERVER="postgres"
POSTGRES_PORT="5432"
DATABASE_NAME="YOUR_DB_NAME"

# Flask
FLASK_PORT=5000
FLASK_ENV="production"  # or "development"

# SQLAlchemy
SECRET_KEY="Something_secret_goes_here"

# Discord
DISCORD_ADMIN_USER_ID="YOUR_ADMIN_ID"  # Used in entrypoint.sh
DISCORD_REDIRECT_URI="BASE_URL_HERE/callback"
DISCORD_CLIENT_ID="YOUR_CLIENT_ID"
DISCORD_CLIENT_SECRET="YOUR_CLIENT_SECRET"
DISCORD_BOT_TOKEN="YOUR_BOT_TOKEN"

# DB Setup in Docker Container
SETUP_TYPE="setup"   # To setup a new blank DB
#SETUP_TYPE="update" # To update from the 2025 DB without clearing user progress

# Latest Year
YEAR=2026
KEY2025="KEY_HERE"
KEY2026="DIFFERENT_KEY_HERE"
# Add keys for other released years as needed
```

> Your own Discord Bot Token and Client ID must be used

> `SETUP_TYPE` controls whether the database is initialized fresh (`setup`)
> or updated from version 1 (`update`).

> Set the `YEAR` variable to specify the latest challenge year to include
> `(starting from 2025)`. Choosing a year higher than the most recently
> released will cause an error.

> Each year requires a unique key (`KEY####`) to access its challenge data and
> solutions, which must be set in the .env file.

> To obtain KEYs, contact the project owner via
> [Discord](https://discord.com/users/609283782897303554) or by
> [email](mailto:jefethepug@protonmail.com).

---

### Local Development

1. **Clone the repository**:

```bash
git clone https://github.com/JefeThePug/Zorak-Coding-Challenges.git
cd Zorak-Coding-Challenges
```

2. **Install dependencies with uv**:

```bash
uv sync --frozen --no-dev --system
```

3. **Run the initial setup**:

- For a blank DB: `python setup.py`
- To migrate from version 1: `python update_from_2025.py`

4. **Start the application**:

```bash
python -m app.run
```

5. **Visit the app**: [http://127.0.0.1:5000](http://127.0.0.1:5000)

---

### Running with Docker

1. **Build and start containers**:

```bash
docker-compose up --build
```

2. **Access the app**: [http://localhost:5000](http://localhost:5000)

> The Flask app connects to PostgreSQL using the hostname defined in `POSTGRES_SERVER` in your `.env`.

---

## Usage Overview

- **Login** – Authenticate via Discord to track progress.
- **Challenges** – Access version 2 challenges, each with two parts.
- **Submit Solutions** – Correct answers update progress and unlock discussion threads.
- **Admin Tools** – Modular dashboard for managing users, challenges, and releases.

---

## Code Structure Highlights

- **`app/blueprints/`** – Routes organized by functionality: `auth`, `challenge`, `admin`, `main`, `errors`.
- **`app/services/`** – Backend services for cooldowns, progress, and Discord notifications.
- **`app/templating/`** – Global functions and utilities for rendering templates.
- **`setup.py` & `update_from_2025.py`** – Setup a blank DB or migrate from version 1.
- **`app/static/` & `app/templates/`** – Organized media and templates for multiple years, with year-specific style overrides.

---

## Sponsorship

Version 2 now supports sponsorship. Individuals or companies can support the project financially. Sponsors are acknowledged on the site and help maintain and expand new challenges, infrastructure, and features. Contact the project owner for details on sponsoring.

---

## Contributing

Contributions can include:

- Providing new challenge ideas
- Providing feedback or suggestions on frontend UX
- Updating backend services
- Discovering / fixing bugs
- Improving documentation

---

## License

Open-source, intended for educational and community-building use.

---

## Acknowledgments

- Inspired by [Advent of Code](https://adventofcode.com)
- Built for the [Practical Python Discord](https://github.com/practical-python-org)
- Thanks to community members who tested and provided feedback for version 2.

Credit is acknowledged on the website.
