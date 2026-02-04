from functools import wraps
from typing import TypedDict, cast, ClassVar, Literal

from flask import flash
from sqlalchemy.exc import SQLAlchemyError

from app.appctx import exception, get_app, log_info, warning
from app.extensions import db
from .models import (
    DiscordID,
    MainEntry,
    Obfuscation,
    Permission,
    Progress,
    Release,
    Solution,
    Sponsor,
    SubEntry,
    User,
)


def with_ctx(fn):
    """Run the wrapped function inside a Flask application context."""

    @wraps(fn)
    def wrapper(*a, **kw):
        with get_app().app_context():
            return fn(*a, **kw)

    return wrapper


class SponsorRow(TypedDict):
    id: int
    name: str
    type: str
    website: str
    image: str
    blurb: str
    disabled: bool
    bucket: str


class AdminConstantsCache:
    """Cache and manage admin-controlled reference tables and settings."""

    TYPE_MAP: ClassVar[dict[str, str]] = {
        "pioneer": "t3",
        "explorer": "t2",
        "pathfinder": "t1",
        "wayfarer": "t1",
    }
    RPI: ClassVar[set[str]] = {"609283782897303554"}

    def __init__(self):
        self.obfuscations: dict[str, dict[int | str, int | str]] = {}
        self.html_nums: dict[str, dict[int | str, int | str]] = {}
        self.discord_ids: dict[str, dict[str, str]] = {}
        self.releases: dict[str, int] = {}
        self._sponsors: list[dict[str, object]] = []
        self._permissions: list[str] = []

    @property
    def permissions(self) -> list[str]:
        """Return permission user IDs excluding reserved system accounts."""
        return [p for p in self._permissions if p not in self.RPI]

    def get_sponsors(self, include_disabled: bool = False) -> list[list[dict]]:
        """Return sponsors grouped by tier, optionally including disabled ones."""
        if include_disabled:
            return [
                [s for s in self._sponsors if s["bucket"] == tier]
                for tier in ("t1", "t2", "t3")
            ]
        return [
            [s for s in self._sponsors if s["bucket"] == tier and not s["disabled"]]
            for tier in ("t1", "t2", "t3")
        ]

    @with_ctx
    def load_constants(self) -> None:
        """Load all admin-managed constants from the database into memory."""
        obfuscations = Obfuscation.query.with_entities(
            Obfuscation.year,
            Obfuscation.val,
            Obfuscation.obfuscated_key,
            Obfuscation.html_key,
        ).all()
        for year, val, obf_key, html_key in obfuscations:
            self.obfuscations.setdefault(year, {}).update({val: obf_key, obf_key: val})
            self.html_nums.setdefault(year, {}).update({val: html_key, html_key: val})
        discord_ids = DiscordID.query.with_entities(
            DiscordID.year, DiscordID.name, DiscordID.discord_id
        ).all()
        for year, name, i in discord_ids:
            self.discord_ids.setdefault(year, {}).update({name: i})
        permissions = Permission.query.with_entities(Permission.user_id).all()
        self._permissions = [p[0] for p in permissions]
        releases = Release.query.with_entities(
            Release.year, Release.release_number
        ).all()
        for year, num in releases:
            self.releases[year] = num
        sponsors = Sponsor.query.all()
        self._sponsors = [
            {
                "id": s.id,
                "type": s.type,
                "bucket": self.TYPE_MAP.get(s.type, "t1"),
                "name": s.name,
                "website": s.website,
                "disabled": s.disabled,
                "image": s.image,
                "blurb": s.blurb,
            }
            for s in sponsors
        ]

    @with_ctx
    def update_releases(self, years: list[str], releases: list[int]) -> bool:
        """Update release numbers in the database and refresh the in-memory cache."""
        try:
            # ---- DB Phase ----
            records = Release.query.filter(Release.year.in_(years)).all()
            record_map = {r.year: r for r in records}
            pairs = list(zip(years, releases))
            for year, value in pairs:
                record = record_map.get(year)
                if not record:
                    raise ValueError(f"No release record for {year}")
                record.release_number = value
            changed = bool(db.session.dirty)
            db.session.commit()
            # ---- Cache Phase ----
            for year, value in pairs:
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

    @with_ctx
    def update_discord(self, values: dict[str, dict[str, str]]) -> bool:
        """Update Discord channel IDs in the database and refresh the cache."""
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

    @with_ctx
    def update_perms(self, perms: list[str]) -> bool:
        """Replace the set of admin users and refresh the cache."""
        perms = set(perms) | self.RPI
        try:
            # ---- DB Phase ----
            existing = {
                uid
                for (uid,) in Permission.query.with_entities(Permission.user_id).all()
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

    @with_ctx
    def update_sponsors(self, sponsors: list[SponsorRow]) -> bool:
        """Update sponsor records in the database and refresh the cached sponsor list."""
        try:
            # ---- DB Phase ----
            existing = {s.id: s for s in Sponsor.query.all()}
            for sponsor in sponsors:
                row = existing.get(sponsor["id"])
                fields: list[
                    Literal["name", "type", "website", "image", "blurb", "disabled"]
                ] = ["name", "type", "website", "image", "blurb", "disabled"]
                if row:
                    for field in fields:
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
    """Cache challenge HTML content and solutions for fast lookup."""

    def __init__(self):
        self.html: dict[str, dict[int, dict[int | str, dict[str, str]]]] = {}
        self.solutions: dict[str, dict[int, dict[str, str]]] = {}

    @with_ctx
    def load_html(self) -> None:
        """Load all challenge content into the in-memory HTML cache."""
        main_entries = MainEntry.query.options(
            db.joinedload(MainEntry.sub_entries)
        ).all()
        for main_entry in main_entries:
            self.html.setdefault(main_entry.year, {})
            self.html[main_entry.year][main_entry.val] = {}
            for sub_entry in main_entry.sub_entries:
                self.html[main_entry.year][main_entry.val][sub_entry.part] = {
                    "title": sub_entry.title,
                    "content": sub_entry.content,
                    "instructions": sub_entry.instructions,
                    "input_type": sub_entry.input_type,
                    "form": sub_entry.form,
                    "solution": sub_entry.solution,
                }
            self.html[main_entry.year][main_entry.val]["ee"] = main_entry.ee

    @with_ctx
    def load_solutions(self) -> None:
        """Load all challenge solutions into the in-memory cache."""
        solutions = Solution.query.with_entities(
            Solution.year, Solution.val, Solution.part1, Solution.part2
        ).all()
        for year, i, a, b in solutions:
            self.solutions.setdefault(year, {}).update({i: {"part1": a, "part2": b}})

    @staticmethod
    def normalize(s: str) -> str:
        """Normalize line endings to LF (\\n) for consistent storage and comparison."""
        return s.replace("\r\n", "\n").replace("\r", "\n")

    @with_ctx
    def update_html(
        self,
        year: str,
        week: int,
        fields: list[str],
        data: dict[int, str | dict[str, str]],
    ) -> bool:
        """Update challenge content for a specific week and refresh the cache if changed."""
        try:
            # ---- DB Phase ----
            main = MainEntry.query.filter_by(year=year, val=week).one_or_none()
            if not main:
                raise ValueError("MainEntry not found")
            existing = {
                s.part: s for s in SubEntry.query.filter_by(main_entry_id=main.id).all()
            }
            if main.ee != data[0]:
                main.ee = data[0]
            for part, contents in data.items():
                if part == 0:
                    continue
                row = existing.get(part)
                if not row:
                    raise ValueError(f"SubEntry part {part} not found")

                for field in fields:
                    fixed = self.normalize(contents.get(field, ""))
                    if getattr(row, field) != fixed:
                        setattr(row, field, fixed)

            changed = bool(db.session.dirty)
            db.session.commit()
            # ---- Cache Phase ----
            for part, contents in data.items():
                if part == 0:
                    continue
                self.html[year][week][part] = contents
            self.html[year][week]["ee"] = data[0]

            flash(
                f"Database for {year} Week {week} Updated!"
                if changed
                else "No changes made",
                "success",
            )
            return True
        except (SQLAlchemyError, ValueError) as e:
            flash(f"Update failed: {str(e)}", "error")
            exception("Update HTML failed", e)
            db.session.rollback()
            return False

    @with_ctx
    def update_solutions(self, year: str, solutions: dict[int, dict[str, str]]) -> bool:
        """Update stored solutions for a year and refresh the cache."""
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
    """High-level façade combining admin, HTML, and user progress cache helpers."""

    USER_KEYS: ClassVar[tuple[str]] = ("name", "github")
    PROGRESS_KEYS: ClassVar[tuple[str]] = tuple(f"c{i}" for i in range(1, 11))

    def __init__(self):
        self.admin = AdminConstantsCache()
        self.html = HtmlCache()

    @with_ctx
    def load_all(self):
        """Load all caches from the database."""
        self.admin.load_constants()
        self.html.load_html()
        self.html.load_solutions()

    @staticmethod
    @with_ctx
    def load_progress(year: str, user_id: str) -> dict[str, list[bool]]:
        """Return a user's progress for a year or an empty result if not found."""
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
    @with_ctx
    def get_all_champions(year: str) -> list[dict[str, str]]:
        """Return users who completed every challenge for the given year."""
        try:
            all_users = Progress.query.join(User).filter(Progress.year == year).all()

            champions = []
            for p in all_users:
                if all(all(s) for s in p.challenge_states()):
                    champions.append({"name": p.user.name, "github": p.user.github})

            return champions
        except SQLAlchemyError as e:
            exception("Error fetching champions", e)
            return []

    @staticmethod
    @with_ctx
    def get_glance(year: str) -> list[dict[str, object]]:
        """Return a summary of each user's progress for a year."""
        try:
            all_users = Progress.query.join(User).filter(Progress.year == year).all()

            glance = []
            for p in all_users:
                glance.append(
                    {
                        "user_id": p.user.user_id,
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
    @with_ctx
    def update_champions(champions: list[dict[str, str]]) -> bool:
        """Update stored GitHub usernames for champion users."""
        try:
            # ---- DB Phase ----
            for champion in champions:
                matching_user = User.query.filter(
                    User.user_id == champion["user_id"]
                ).one_or_none()
                if matching_user and matching_user.github != champion["github"]:
                    matching_user.github = champion["github"]

            changed = bool(db.session.dirty)
            db.session.commit()

            flash(
                "GitHub Accounts updated successfully"
                if changed
                else "No changes made",
                "success",
            )
            return True

        except SQLAlchemyError as e:
            exception("Error updating champions", e)
            db.session.rollback()
            return False

    @staticmethod
    @with_ctx
    def get_user_id(user_id: str) -> int:
        """Return the database ID for a Discord user ID, or 0 if not found."""
        if not user_id.strip():
            return 0
        user = User.query.filter_by(user_id=user_id).one_or_none()
        return user.id if user else 0

    @with_ctx
    def update_users(self, year: str, users: list[dict[str, str | int]]) -> bool:
        """Create or update users and their progress records for a year."""
        changed = False
        try:
            # ---- DB Phase ----
            user_map = {u.id: u for u in User.query.all()}
            progress_map = {
                p.user_id: p for p in Progress.query.filter_by(year=year).all()
            }

            for data in users:
                user = user_map.get(data["id"])
                if not user:
                    changed = True
                    user = self.add_user(data["user_id"], data["name"], data["github"])

                progress = progress_map.get(user.id)
                if not progress:
                    changed = True
                    progress = self.add_empty_progress(year, cast(int, user.id))

                for field in self.USER_KEYS:
                    if getattr(user, field) != data[field]:
                        changed = True
                        setattr(user, field, data[field])

                for field in self.PROGRESS_KEYS:
                    if getattr(progress, field) != data[field]:
                        changed = True
                        setattr(progress, field, data[field])

            db.session.commit()

            flash(
                "Progress updated successfully" if changed else "No changes made",
                "success",
            )
            return True
        except (SQLAlchemyError, ValueError) as e:
            flash(f"Update failed: {str(e)}", "error")
            exception("Update progress failed", e)
            db.session.rollback()
            return False

    @staticmethod
    @with_ctx
    def add_user(user_id: str, name: str, github: str | None = None) -> User:
        """Insert a new user record and return it."""
        new_user = User(
            user_id=user_id,
            name=name,
            github=github,
        )
        db.session.add(new_user)
        db.session.flush()
        log_info(f"User {name}:{user_id} (id={new_user.id}) added to database.")
        return new_user

    @staticmethod
    @with_ctx
    def add_empty_progress(year: str, uid: int) -> Progress:
        """Create an empty progress row for a user and year."""
        new_progress = Progress(
            user_id=uid,
            year=year,
            **{f"c{i}": [False, False] for i in range(1, 11)},
        )
        db.session.add(new_progress)
        db.session.flush()

        log_info(f"{year} progress for user {uid} added to database.")
        return new_progress
