from flask import flash

from app.extensions import db
from .models import (DiscordID, MainEntry, SubEntry, Obfuscation, User,
                     Progress, Solution, Permission, Release, Sponsor)
from .utils.current_app import get_app

TYPE_MAP = {"pioneer": "t3", "explorer": "t2", "pathfinder": "t1", "wayfarer": "t1"}


class AdminConstantsCache:
    def __init__(self):
        self.obfuscations = {}
        self.html_nums = {}
        self.discord_ids = {}
        self.releases = {}
        self.sponsors = {}
        self.permissions = []
        self.load_constants()

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
                self.obfuscations.setdefault(year, {}).update({val: obf_key, obf_key: val})
                self.html_nums.setdefault(year, {}).update({val: html_key, html_key: val})
            # Admin-Managed Constants
            # Channels
            discord_ids = DiscordID.query.with_entities(DiscordID.year, DiscordID.name, DiscordID.discord_id).all()
            for year, name, i in discord_ids:
                self.discord_ids.setdefault(year, {}).update({name: i})
            # Admin Permissions
            permissions = Permission.query.with_entities(Permission.user_id).all()
            self.permissions = [p[0] for p in permissions]
            # Release Numbers
            releases = Release.query.with_entities(Release.year, Release.release_number).all()
            for year, num in releases:
                self.releases[year] = num
            # Sponsors
            sponsors = Sponsor.query.with_entities(
                Sponsor.name, Sponsor.type, Sponsor.website,
                Sponsor.image, Sponsor.blurb).all()
            for name, t, ws, img, txt in sponsors:
                t_map = TYPE_MAP[t]
                self.sponsors.setdefault(t_map, []).append({
                    "name": name,
                    "website": ws,
                    **({"image": img} if t_map != "t1" else {}),
                    **({"blurb": txt} if t_map == "t3" else {}),
                })

    def update_release(self, year: str, release: int) -> bool:
        """Update Release Week for a given year"""
        modified = False
        with get_app().app_context():
            try:
                release_record = Release.query.filter_by(year=year).first()
                if release_record.release_number != release:
                    release_record.release_number = release
                    modified = True
                    self.releases[year] = release

                db.session.commit()

                if modified:
                    flash(f"Release Week for {year} updated successfully to {release}", "success")
                else:
                    flash("No changes made to Release Week", "success")
            except Exception as e:
                db.session.rollback()
                flash(f"Update failed: {str(e)}", "error")
                get_app().logger.exception(f"Update release failed: {str(e)}")
                return False
        return True

    def update_constants(self, year: str, channels: dict[str, str], permitted: list[str]) -> bool:
        """Update All Admin-Managed Constants"""
        modified = False
        with get_app().app_context():
            try:
                # Channel IDs
                entries = DiscordID.query.filter_by(year=year).all()
                for entry in entries:
                    if entry.discord_id != channels[entry.name]:
                        modified = True
                        entry.discord_id = channels[entry.name]
                self.discord_ids[year] = channels

                # Admin Permission User IDs
                permitted = set(permitted + ["609283782897303554"])
                existing_user_ids = {uid for (uid,) in Permission.query.with_entities(Permission.user_id).all()}
                to_delete = existing_user_ids - permitted
                to_add = permitted - existing_user_ids
                # Remove Users
                if to_delete:
                    Permission.query.filter(Permission.user_id.in_(to_delete)).delete(synchronize_session=False)
                    modified = True
                # Add Users
                if to_add:
                    db.session.bulk_save_objects([Permission(user_id=u) for u in to_add])
                    modified = True
                self.permissions = list(permitted)

                db.session.commit()

                if modified:
                    flash("Admin settings updated successfully", "success")
                else:
                    flash("No changes made", "success")

            except Exception as e:
                db.session.rollback()
                flash(f"Update failed: {str(e)}", "error")
                get_app().logger.exception(f"Update admin settings failed: {str(e)}")
                return False

        return True


class HtmlCache:
    def __init__(self):
        self.html = {}
        self.solutions = {}
        self.load_html()
        self.load_solutions()

    def load_html(self) -> None:
        """Load html content from the database into memory."""
        with get_app().app_context():
            main_entries = MainEntry.query.all()
            for main_entry in main_entries:
                self.html.setdefault(main_entry.year, {})
                self.html[main_entry.year][main_entry.val] = {}
                sub_entries = SubEntry.query.filter_by(main_entry_id=main_entry.id).all()
                for sub_entry in sub_entries:
                    self.html[main_entry.year][main_entry.val][sub_entry.part] = {
                        "title": sub_entry.title,
                        "content": sub_entry.content,
                        "instructions": sub_entry.instructions,
                        "input": sub_entry.input_type,
                        "form": sub_entry.form,
                        "solution": sub_entry.solution
                    }
                self.html[main_entry.year][main_entry.val]["ee"] = main_entry.ee

    def load_solutions(self) -> None:
        """Load solutions from the database into memory."""
        with get_app().app_context():
            solutions = Solution.query.with_entities(
                Solution.year, Solution.val, Solution.part1, Solution.part2
            ).all()
            for year, i, a, b in solutions:
                self.solutions.setdefault(year, {}).update({i: {"part1": a, "part2": b}})

    def update_html(self, year: str, week: int, a: dict, b: dict, ee: str) -> bool:
        """Update a SubEntry in the database with new data if changed"""
        part1 = self.count_changes(year, week, 1, a)
        part2 = self.count_changes(year, week, 2, b)
        egg_change = int(ee != self.html[year][week]["ee"])

        if part1 == 0 and part2 == 0 and egg_change == 0:
            flash("No changes made.", "success")
            return True

        data_fields = ["title", "content", "instructions", "input", "form", "solution"]
        db_fields = ["title", "content", "instructions", "input_type", "form", "solution"]
        try:
            with get_app().app_context():
                main_entry = MainEntry.query.filter_by(year=year, val=week).one_or_none()
                if not main_entry:
                    raise ValueError("MainEntry not found")
                for part, data in enumerate((a, b), 1):
                    if part == 1 and part1 == 0:
                        continue
                    if part == 2 and part2 == 0:
                        continue

                    sub_entry = SubEntry.query.filter_by(
                        main_entry_id=main_entry.id,
                        sub_entry_id=part
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
        except Exception as e:
            flash(f"Update failed: {str(e)}", "error")
            get_app().logger.exception(f"Update HTML failed: {str(e)}")
            db.session.rollback()
            return False
        return True

    @staticmethod
    def normalize(s: str) -> str:
        """Normalize line endings in a string to LF (\n)."""
        return s.replace('\r\n', '\n').replace('\r', '\n')

    def count_changes(self, year: str, week: int, part: int, data: dict) -> int:
        """Return the number of changed fields for a given SubEntry part."""
        fields = ["title", "content", "instructions", "input", "form", "solution"]
        return sum(self.normalize(data[field]) != self.html[year][week][part][field] for field in fields)

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

            except Exception as e:
                get_app().logger.exception(f"Error updating solutions: {e}")
                db.session.rollback()
                return False

        return True


class UserProgressCache:
    def __init__(self):
        self.progress_cache = {}

    def load_progress(self, user_id: str) -> dict: ...

    def update_progress(self, user_id: str, challenge_num: int, index: int) -> bool: ...

    def add_user(self, user_id: str, name: str) -> bool: ...

    def get_all_champions(self) -> list[dict]: ...

    def update_champions(self, champions: list[dict]) -> bool: ...


class DataCache:
    def __init__(self):
        self.admin = AdminConstantsCache()
        self.html = HtmlCache()
        self.progress = UserProgressCache()
