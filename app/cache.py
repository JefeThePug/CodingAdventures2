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


class AdminConstantsCache:
    def __init__(self):
        self.obfuscations = {}
        self.html_nums = {}
        self.discord_ids = {}
        self.releases = {}
        self.sponsors = {}
        self.permissions = []

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
            self.permissions = [p[0] for p in permissions]
            # Release Numbers
            releases = Release.query.with_entities(
                Release.year, Release.release_number
            ).all()
            for year, num in releases:
                self.releases[year] = num
            # Sponsors
            sponsors = Sponsor.query.with_entities(
                Sponsor.name,
                Sponsor.type,
                Sponsor.website,
                Sponsor.image,
                Sponsor.blurb,
            ).all()
            for name, t, ws, img, txt in sponsors:
                t_map = TYPE_MAP[t]
                self.sponsors.setdefault(t_map, []).append(
                    {
                        "type": t,
                        "name": name,
                        "website": ws,
                        **({"image": img} if t_map != "t1" else {}),
                        **({"blurb": txt} if t_map == "t3" else {}),
                    }
                )

    def update_releases(self, years: list[str], releases: list[int]) -> bool:
        """Update Release Week for a given year"""
        modified = False
        try:
            records = (Release.query.filter(Release.year.in_(years)).all())
            record_map = {r.year: r for r in records}

            modified = False
            for year, value in zip(years, releases):
                record = record_map.get(year)
                if not record:
                    raise ValueError(f"No release record for {year}")
                if record.release_number != value:
                    record.release_number = value
                    self.releases[year] = value
                    modified = True

            db.session.commit()

            flash(
                "Release weeks updated successfully" if modified else "No changes made to release weeks",
                "success"
            )
            return True

        except (SQLAlchemyError, ValueError) as e:
            db.session.rollback()
            flash(f"Update failed: {e}", "error")
            exception("Update releases failed", e)
            return False


    def update_constants(
        self, year: str, chan: dict[str, str], perms: list[str]
    ) -> bool:
        """Update All Admin-Managed Constants"""
        modified = False
        with get_app().app_context():
            try:
                # Channel IDs
                entries = DiscordID.query.filter_by(year=year).all()
                for entry in entries:
                    if entry.discord_id != chan[entry.name]:
                        modified = True
                        entry.discord_id = chan[entry.name]
                self.discord_ids[year] = chan

                # Admin Permission User IDs
                perms = set(perms + ["609283782897303554"])
                existing_user_ids = {
                    uid
                    for (uid,) in Permission.query.with_entities(
                        Permission.user_id
                    ).all()
                }
                to_delete = existing_user_ids - perms
                to_add = perms - existing_user_ids
                # Remove Users
                if to_delete:
                    Permission.query.filter(Permission.user_id.in_(to_delete)).delete(
                        synchronize_session=False
                    )
                    modified = True
                # Add Users
                if to_add:
                    db.session.bulk_save_objects(
                        [Permission(user_id=u) for u in to_add]
                    )
                    modified = True
                self.permissions = list(perms)

                db.session.commit()

                if modified:
                    flash("Admin settings updated successfully", "success")
                else:
                    flash("No changes made", "success")

            except Exception as e:
                db.session.rollback()
                flash(f"Update failed: {str(e)}", "error")
                exception("Update admin settings failed", e)
                return False

        return True

    @staticmethod
    def get_all_sponsors(include_disabled:bool = False) -> tuple[list[dict], list[dict], list[dict]]:
        """Get progress for all users that completed 10 challenges for a given year."""
        try:
            with get_app().app_context():
                query = Sponsor.query
                if not include_disabled:
                    query = query.filter(Sponsor.disabled.is_(False))
                all_sponsors = query.all()

                t1, t2, t3 = [], [], []
                for sponsor in all_sponsors:
                    base = {
                        "type": sponsor.type,
                        "name": sponsor.name,
                        "website": sponsor.website,
                    }
                    if include_disabled:
                        base["disabled"] = sponsor.disabled
                    if TYPE_MAP[sponsor.type] == "t1":
                        t1.append(base)
                    elif TYPE_MAP[sponsor.type] == "t2":
                        t2.append({**base, "image": sponsor.image})
                    elif TYPE_MAP[sponsor.type] == "t3":
                        t3.append(
                            {**base, "image": sponsor.image, "blurb": sponsor.blurb}
                        )

                return t1, t2, t3
        except SQLAlchemyError as e:
            exception("Error fetching champions", e)
            return [], [], []


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
                        "input": sub_entry.input_type,
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

    def update_html(self, year: str, week: int, a: dict, b: dict, ee: str) -> bool:
        """Update a SubEntry in the database with new data if changed"""
        part1 = self.count_changes(year, week, 1, a)
        part2 = self.count_changes(year, week, 2, b)
        egg_change = int(ee != self.html[year][week]["ee"])

        if part1 == 0 and part2 == 0 and egg_change == 0:
            flash("No changes made.", "success")
            return True

        data_fields = ["title", "content", "instructions", "input", "form", "solution"]
        db_fields = [
            "title",
            "content",
            "instructions",
            "input_type",
            "form",
            "solution",
        ]
        try:
            with get_app().app_context():
                main_entry = MainEntry.query.filter_by(
                    year=year, val=week
                ).one_or_none()
                if not main_entry:
                    raise ValueError("MainEntry not found")
                for part, data in enumerate((a, b), 1):
                    if part == 1 and part1 == 0:
                        continue
                    if part == 2 and part2 == 0:
                        continue

                    sub_entry = SubEntry.query.filter_by(
                        main_entry_id=main_entry.id, sub_entry_id=part
                    ).one_or_none()
                    if not sub_entry:
                        raise ValueError(f"SubEntry part {part} not found")
                    for data_field, db_field in zip(data_fields, db_fields):
                        fixed = self.normalize(data[data_field])
                        if fixed != self.html[year][week][part][data_field]:
                            setattr(sub_entry, db_field, fixed)

                if egg_change:
                    main_entry.ee = ee

                db.session.commit()

            flash(f"Database for Week {week} Successfully Updated!", "success")
            self.load_html()
        except SQLAlchemyError as e:
            flash(f"Update failed: {str(e)}", "error")
            exception("Update HTML failed", e)
            db.session.rollback()
            return False
        return True

    @staticmethod
    def normalize(s: str) -> str:
        """Normalize line endings in a string to LF (\n)."""
        return s.replace("\r\n", "\n").replace("\r", "\n")

    def count_changes(self, year: str, week: int, part: int, data: dict) -> int:
        """Return the number of changed fields for a given SubEntry part."""
        fields = ["title", "content", "instructions", "input", "form", "solution"]
        return sum(
            self.normalize(data[field]) != self.html[year][week][part][field]
            for field in fields
        )

    def update_solutions(self, year: str, solutions: dict[int, dict[str, str]]) -> bool:
        """Update solutions in database"""
        modified = False
        with get_app().app_context():
            try:
                for i, parts in solutions.items():
                    solution = Solution.query.filter_by(year=year, val=i).one_or_none()
                    if not solution:
                        raise ValueError(f"Solution not found for year={year}, val={i}")
                    for part in ["part1", "part2"]:
                        if getattr(solution, part) != parts[part]:
                            setattr(solution, part, parts[part])
                            modified = True

                db.session.commit()
                self.load_solutions()

                if modified:
                    flash("Solutions updated successfully", "success")
                else:
                    flash("No changes made", "success")

            except SQLAlchemyError as e:
                exception("Error updating solutions", e)
                db.session.rollback()
                return False

        return True


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
