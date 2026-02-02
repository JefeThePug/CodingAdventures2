from flask import flash
from sqlalchemy.exc import SQLAlchemyError

from app.appctx import get_app, warning, exception, log_info
from app.extensions import db
from .models import (
    DiscordID,
    MainEntry,
    SubEntry,
    Obfuscation,
    User,
    Progress,
    Solution,
    Permission,
    Release,
    Sponsor,
)

TYPE_MAP = {"pioneer": "t3", "explorer": "t2", "pathfinder": "t1", "wayfarer": "t1"}
RPI = {"609283782897303554"}


class AdminConstantsCache:
    def __init__(self):
        self.obfuscations = {}
        self.html_nums = {}
        self.discord_ids = {}
        self.releases = {}
        self._sponsors = []
        self._permissions = []

    def get_sponsors(self, include_disabled: bool = False) -> list[list[dict]]:
        """Get all sponsors or only enabled sponsors from the database"""
        if include_disabled:
            return [
                [s for s in self._sponsors if s["bucket"] == tier]
                for tier in ("t1", "t2", "t3")
            ]
        return [
            [s for s in self._sponsors if s["bucket"] == tier and not s["disabled"]]
            for tier in ("t1", "t2", "t3")
        ]

    @property
    def permissions(self) -> list[str]:
        return [p for p in self._permissions if p not in RPI]

    def load_constants(self) -> None:
        """Load all pseudo-constant data from the database into memory."""
        with get_app().app_context():
            # Total Constants
            obfuscations = Obfuscation.query.with_entities(
                Obfuscation.year,
                Obfuscation.val,
                Obfuscation.obfuscated_key,
                Obfuscation.html_key,
            ).all()
            for year, val, obf_key, html_key in obfuscations:
                self.obfuscations.setdefault(year, {}).update(
                    {val: obf_key, obf_key: val}
                )
                self.html_nums.setdefault(year, {}).update(
                    {val: html_key, html_key: val}
                )
            # Admin-Managed Constants
            # Channels
            discord_ids = DiscordID.query.with_entities(
                DiscordID.year, DiscordID.name, DiscordID.discord_id
            ).all()
            for year, name, i in discord_ids:
                self.discord_ids.setdefault(year, {}).update({name: i})
            # Admin Permissions
            permissions = Permission.query.with_entities(Permission.user_id).all()
            self._permissions = [p[0] for p in permissions]
            # Release Numbers
            releases = Release.query.with_entities(
                Release.year, Release.release_number
            ).all()
            for year, num in releases:
                self.releases[year] = num
            # Sponsors
            sponsors = Sponsor.query.all()
            self._sponsors = [
                {
                    "id": s.id,
                    "type": s.type,
                    "bucket": TYPE_MAP[s.type],
                    "name": s.name,
                    "website": s.website,
                    "disabled": s.disabled,
                    "image": s.image,
                    "blurb": s.blurb,
                }
                for s in sponsors
            ]

    def update_releases(self, years: list[str], releases: list[int]) -> bool:
        """Update Release Weeks for every year"""
        try:
            # ---- DB Phase ----
            records = Release.query.filter(Release.year.in_(years)).all()
            record_map = {r.year: r for r in records}
            for year, value in zip(years, releases):
                record = record_map.get(year)
                if not record:
                    raise ValueError(f"No release record for {year}")
                record.release_number = value
            changed = bool(db.session.dirty)
            db.session.commit()
            # ---- Cache Phase ----
            for year, value in zip(years, releases):
                self.releases[year] = value

            flash(
                "Release weeks updated successfully"
                if changed
                else "No changes made to release weeks",
                "success",
            )
            return True
        except (SQLAlchemyError, ValueError) as e:
            db.session.rollback()
            flash(f"Update failed: {e}", "error")
            exception("Update releases failed", e)
            return False

    def update_discord(self, values: dict[str, dict[str, str]]) -> bool:
        """Update Discord IDs for channels for each year, a guild ID, and a verified role ID"""
        try:
            # ---- DB Phase ----
            for year, mapping in values.items():
                entries = DiscordID.query.filter_by(year=year).all()
                for entry in entries:
                    entry.discord_id = mapping.get(entry.name, "")

            changed = bool(db.session.dirty)
            db.session.commit()
            # ---- Cache Phase ----
            for year, mapping in values.items():
                self.discord_ids[year] = mapping

            flash(
                "Discord ID settings updated successfully"
                if changed
                else "No changes made",
                "success",
            )
            return True
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f"Update failed: {e}", "error")
            exception("Update Discord IDs failed", e)
            return False

    def update_perms(self, perms: list[str]) -> bool:
        """Update users with Admin permissions"""
        perms = set(perms) | RPI
        try:
            # ---- DB Phase ----
            existing = {
                uid for uid, in Permission.query.with_entities(Permission.user_id).all()
            }
            to_delete = existing - perms
            to_add = perms - existing
            if to_delete:
                Permission.query.filter(Permission.user_id.in_(to_delete)).delete(
                    synchronize_session=False
                )
            if to_add:
                db.session.bulk_save_objects([Permission(user_id=u) for u in to_add])

            changed = bool(to_delete or to_add)
            db.session.commit()
            # ---- Cache Phase ----
            self._permissions = list(perms)

            flash(
                "Admin settings updated successfully" if changed else "No changes made",
                "success",
            )
            return True
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f"Update failed: {str(e)}", "error")
            exception("Update admin settings failed", e)
            return False

    def update_sponsors(self, sponsors: list[dict]) -> bool:
        """Update the list of sponsors and their contents in the database"""
        try:
            # ---- DB Phase ----
            existing = {s.id: s for s in Sponsor.query.all()}
            for sponsor in sponsors:
                row = existing.get(sponsor["id"])

                if row:
                    for field in (
                        "name",
                        "type",
                        "website",
                        "image",
                        "blurb",
                        "disabled",
                    ):
                        new = sponsor[field]
                        if getattr(row, field) != new:
                            setattr(row, field, new)
                else:
                    db.session.add(
                        Sponsor(
                            **{
                                k: v
                                for k, v in sponsor.items()
                                if k not in ("id", "bucket")
                            }
                        )
                    )

            changed = bool(db.session.dirty or db.session.new)
            db.session.commit()
            # ---- Cache Phase ----
            self._sponsors = sponsors

            flash(
                "Sponsors updated successfully" if changed else "No changes made",
                "success",
            )
            return True
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f"Update failed: {str(e)}", "error")
            exception("Update sponsors settings failed", e)
            return False


class HtmlCache:
    def __init__(self):
        self.html = {}
        self.solutions = {}

    def load_html(self) -> None:
        """Load html content from the database into memory."""
        with get_app().app_context():
            main_entries = MainEntry.query.all()
            for main_entry in main_entries:
                self.html.setdefault(main_entry.year, {})
                self.html[main_entry.year][main_entry.val] = {}
                sub_entries = SubEntry.query.filter_by(
                    main_entry_id=main_entry.id
                ).all()
                for sub_entry in sub_entries:
                    self.html[main_entry.year][main_entry.val][sub_entry.part] = {
                        "title": sub_entry.title,
                        "content": sub_entry.content,
                        "instructions": sub_entry.instructions,
                        "input_type": sub_entry.input_type,
                        "form": sub_entry.form,
                        "solution": sub_entry.solution,
                    }
                self.html[main_entry.year][main_entry.val]["ee"] = main_entry.ee

    def load_solutions(self) -> None:
        """Load solutions from the database into memory."""
        with get_app().app_context():
            solutions = Solution.query.with_entities(
                Solution.year, Solution.val, Solution.part1, Solution.part2
            ).all()
            for year, i, a, b in solutions:
                self.solutions.setdefault(year, {}).update(
                    {i: {"part1": a, "part2": b}}
                )

    @staticmethod
    def normalize(s: str) -> str:
        """Normalize line endings in a string to LF (\n)."""
        return s.replace("\r\n", "\n").replace("\r", "\n")

    def update_html(
        self, year: str, week: int, fields: list[str], data: dict[int, dict[str, str]]
    ) -> bool:
        """Update a SubEntry in the database with new data if changed"""
        try:
            # ---- DB Phase ----
            main = MainEntry.query.filter_by(year=year, val=week).one_or_none()
            if not main:
                raise ValueError("MainEntry not found")
            existing = {
                s.sub_entry_id: s
                for s in SubEntry.query.filter_by(main_entry_id=main.id).all()
            }
            for part, contents in data.items():
                row = existing.get(part)
                if not row:
                    raise ValueError(f"SubEntry part {part} not found")

                for field in fields:
                    fixed = self.normalize(contents[field])
                    if getattr(row, field) != fixed:
                        setattr(row, field, fixed)

            changed = bool(db.session.dirty)
            db.session.commit()
            # ---- Cache Phase ----
            self.html[year][week] = data

            flash(
                f"Database for Week {week} Successfully Updated!" if changed else "",
                "success",
            )
            return True
        except (SQLAlchemyError, ValueError) as e:
            flash(f"Update failed: {str(e)}", "error")
            exception("Update HTML failed", e)
            db.session.rollback()
            return False

    def update_solutions(self, year: str, solutions: dict[int, dict[str, str]]) -> bool:
        """Update solutions in database"""
        existing = {s.val: s for s in Solution.query.filter_by(year=year).all()}
        try:
            # ---- DB Phase ----
            for i, parts in solutions.items():
                solution = existing.get(i)
                if not solution:
                    raise ValueError(f"Solution not found for year={year}, val={i}")
                for part in ("part1", "part2"):
                    if getattr(solution, part) != parts[part]:
                        setattr(solution, part, parts[part])

            changed = bool(db.session.dirty)
            db.session.commit()
            # ---- Cache Phase ----
            self.solutions[year] = solutions

            flash(
                "Solutions updated successfully" if changed else "No changes made",
                "success",
            )
            return True
        except (SQLAlchemyError, ValueError) as e:
            flash(f"Update failed: {str(e)}", "error")
            exception("Error updating solutions", e)
            db.session.rollback()
            return False


class DataCache:
    def __init__(self):
        self.admin = AdminConstantsCache()
        self.html = HtmlCache()

    def load(self):
        self.admin.load_constants()
        self.html.load_html()
        self.html.load_solutions()

    @staticmethod
    def load_progress(year: str, user_id: str) -> dict:
        """Query user progress from the database. Returns a dict if found, else an empty dict."""
        with get_app().app_context():
            try:
                progress = (
                    Progress.query.join(User)
                    .filter(User.user_id == user_id, Progress.year == year)
                    .one_or_none()
                )
                if progress is None:
                    warning(f"User {user_id} not found in database when loading data")
                    return {}
                return {f"c{i}": getattr(progress, f"c{i}") for i in range(1, 11)}
            except SQLAlchemyError as e:
                exception(f"Failed to load progress for user {user_id}", e)
                return {}

    @staticmethod
    def update_progress(year: str, user_id: str, c_num: int, index: int) -> bool:
        """Update individual user progress in the database and refresh the cache."""
        with get_app().app_context():
            progress = (
                Progress.query.join(User)
                .filter(User.user_id == user_id, Progress.year == year)
                .one_or_none()
            )
            if progress is None:
                warning(f"User {user_id} not found in database when updating data.")
                return False
            col_name = f"c{c_num}"
            challenge = getattr(progress, col_name, None)
            if challenge is None:
                warning(
                    f"Unexpected error with updating challenge. {progress=} {challenge=}"
                )
                return False
            if not (0 <= index < len(challenge)):
                warning(
                    f"Progress update: Index out of bounds {index=}, len={len(challenge)}"
                )
                return False
            challenge = challenge[:index] + [True] + challenge[index + 1 :]
            setattr(progress, col_name, challenge)
            db.session.commit()
        return True

    @staticmethod
    def add_user(user_id: str, name: str) -> bool:
        """Insert a new progress record into the database."""
        # changed = bool(
        #     db.session.dirty or
        #     db.session.new or
        #     db.session.deleted
        # )
        app = get_app()
        try:
            with app.app_context():
                new_user = User(
                    user_id=user_id,
                    name=name,
                    github="",
                )
                db.session.add(new_user)
                db.session.flush()
                for year in range(2025, app.config["CURRENT_YEAR"] + 1):
                    new_progress = Progress(
                        user_id=new_user.id,
                        year=f"{year}",
                        **{f"c{i}": [False, False] for i in range(1, 11)},
                    )
                    db.session.add(new_progress)
                db.session.commit()
                log_info(f"User {name}:{user_id} (id={new_user.id}) added to database.")
            return True
        except SQLAlchemyError as e:
            exception("Error adding user", e)
            db.session.rollback()
            return False

    @staticmethod
    def get_all_champions(year: str) -> list[dict[str, str]]:
        """Get list of all users that completed 10 challenges for a given year."""
        app = get_app()
        try:
            with app.app_context():
                all_users = (
                    Progress.query.join(User).filter(Progress.year == year).all()
                )

                champions = []
                for p in all_users:
                    if all(all(s) for s in p.challenge_states()):
                        champions.append({"name": p.user.name, "github": p.user.github})

                return champions
        except SQLAlchemyError as e:
            exception("Error fetching champions", e)
            return []

    @staticmethod
    def get_glance(year: str) -> list[dict[str, str]]:
        """Get progress of all users for a given year."""
        app = get_app()
        try:
            with app.app_context():
                all_users = (
                    Progress.query.join(User).filter(Progress.year == year).all()
                )

                glance = []
                for p in all_users:
                    glance.append(
                        {
                            "id": p.user.user_id,
                            "name": p.user.name,
                            "github": p.user.github,
                            "progress": p.challenge_states(),
                        }
                    )
            return glance
        except SQLAlchemyError as e:
            exception("Error fetching user progress", e)
            return []

    @staticmethod
    def update_champions(champions: list[dict]) -> bool:
        """Update GitHub account of champions in database"""
        modified = False
        with get_app().app_context():
            try:
                for champion in champions:
                    matching_user = User.query.filter(
                        User.user_id == champion["user_id"]
                    ).one_or_none()
                    if matching_user.github != champion["github"]:
                        matching_user.github = champion["github"]
                        modified = True

                db.session.commit()

                if modified:
                    flash("GitHub Accounts updated successfully", "success")
                else:
                    flash("No changes made", "success")

            except SQLAlchemyError as e:
                exception("Error updating champions", e)
                db.session.rollback()
                return False

        return True
