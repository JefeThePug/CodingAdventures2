from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.appctx import get_app
from app.auth.decorators import admin_only

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin", methods=["GET", "POST"])
@admin_only
def admin():
    return render_template("admin/default.html")


@admin_bp.route("/admin/home")
@admin_only
def admin_home():
    return render_template("admin/home.html")


@admin_bp.route("/admin/release", methods=["GET", "POST"])
@admin_only
def release():
    app = get_app()
    years = list(map(str, range(2025, app.config["CURRENT_YEAR"] + 1)))
    releases = {y: app.data_cache.admin.releases[y] for y in years}

    if request.method == "POST":
        values = []
        for year in years:
            raw = request.form.get(year, "").strip()
            if not raw.isdigit():
                flash(f"{year}: release must be a number 0–10", "error")
                return redirect(url_for("admin.release"))
            values.append(min(10, max(0, int(raw))))
        app.data_cache.admin.update_releases(years, values)
        return redirect(url_for("admin.release"))

    return render_template(
        "admin/release.html",
        years=years,
        release=releases,
    )


@admin_bp.route("/admin/discord", methods=["GET", "POST"])
@admin_only
def discord():
    app = get_app()
    years = list(map(str, range(2025, app.config["CURRENT_YEAR"] + 1)))
    selected_year = request.args.get(
        "year", request.form.get("year", f"{app.config['CURRENT_YEAR']}")
    )
    main = app.data_cache.admin.discord_ids["0"]
    channels = {y: app.data_cache.admin.discord_ids[y] for y in years}

    if request.method == "POST":
        values = {
            selected_year: {
                f"{i}": request.form.get(f"c{i}", "").strip() for i in range(1, 11)
            },
            "0": {key: request.form.get(key, "").strip() for key in ("guild", "role")},
        }
        app.data_cache.admin.update_discord(values)
        return redirect(url_for("admin.discord", year=selected_year))

    return render_template(
        "admin/discord.html",
        years=years,
        selected_year=selected_year,
        guild=main["guild"],
        role=main["role"],
        channels=channels,
    )


@admin_bp.route("/admin/html", methods=["GET", "POST"])
@admin_only
def html():
    app = get_app()
    years = list(map(str, range(2025, app.config["CURRENT_YEAR"] + 1)))
    selected_year = request.args.get(
        "year", request.form.get("year", f"{app.config['CURRENT_YEAR']}")
    )
    selected_week = int(request.args.get("week", request.form.get("week", 1)))
    fields = ["title", "content", "instructions", "input_type", "form", "solution"]
    data = {
        part: app.data_cache.html.html[selected_year][selected_week][part]
        for part in range(1, 3)
    }
    egg = app.data_cache.html.html[selected_year][selected_week]["ee"]

    if request.method == "POST":
        contents = {
            0: request.form.get("easter-egg") or None,
            **{
                i: {cat: request.form.get(f"{cat}{i}") for cat in fields}
                for i in range(1, 3)
            },
        }
        app.data_cache.html.update_html(selected_year, selected_week, fields, contents)
        return redirect(url_for("admin.html", year=selected_year, week=selected_week))

    return render_template(
        "admin/html.html",
        years=years,
        selected_year=selected_year,
        selected_week=selected_week,
        fields=fields,
        data=data,
        egg=egg,
    )


@admin_bp.route("/admin/solutions", methods=["GET", "POST"])
@admin_only
def solutions():
    app = get_app()
    years = list(map(str, range(2025, app.config["CURRENT_YEAR"] + 1)))
    selected_year = request.args.get(
        "year", request.form.get("year", f"{app.config['CURRENT_YEAR']}")
    )
    solution_list = app.data_cache.html.solutions[selected_year]

    if request.method == "POST":
        contents = {
            i: {"part1": request.form.get(f"{i}1"), "part2": request.form.get(f"{i}2")}
            for i in range(1, 11)
        }
        app.data_cache.html.update_solutions(selected_year, contents)
        return redirect(url_for("admin.solutions", year=selected_year))

    return render_template(
        "admin/solutions.html",
        years=years,
        selected_year=selected_year,
        solutions=solution_list,
    )


@admin_bp.route("/admin/users", methods=["GET", "POST"])
@admin_only
def user():
    app = get_app()
    years = list(map(str, range(2025, app.config["CURRENT_YEAR"] + 1)))
    selected_year = request.args.get(
        "year", request.form.get("year", f"{app.config['CURRENT_YEAR']}")
    )
    users = app.data_cache.get_glance(selected_year)

    if request.method == "POST":
        numbers = set(
            int(k)
            for key in request.form
            if "_" in key and (k := key.rsplit("_", 1)[1]).isdigit()
        )
        user_data = [
            {
                "id": int(app.data_cache.get_user_id(request.form.get(f"user_id_{n}"))),
                "user_id": request.form.get(f"user_id_{n}"),
                "name": request.form.get(f"name_{n}") or None,
                "github": request.form.get(f"github_{n}") or None,
                **{
                    f"c{i}": [
                        f"{i}A_{n}" in request.form,
                        f"{i}B_{n}" in request.form,
                    ]
                    for i in range(1, 11)
                },
            }
            for n in sorted(numbers)
            if request.form.get(f"user_id_{n}", "").strip()
        ]
        app.data_cache.update_users(selected_year, user_data)

        return redirect(url_for("admin.user"))

    return render_template(
        "admin/users.html",
        years=years,
        selected_year=selected_year,
        users=users,
    )


@admin_bp.route("/admin/sponsors", methods=["GET", "POST"])
@admin_only
def sponsor():
    app = get_app()
    fields = ["name", "type", "website", "image", "blurb"]
    contents = [fields[:3], fields[:4], fields[:]]
    t1, t2, t3 = app.data_cache.admin.get_sponsors(include_disabled=True)

    if request.method == "POST":
        numbers = set(
            int(k)
            for key in request.form
            if "_" in key and (k := key.rsplit("_", 1)[1]).isdigit()
        )
        bucket = {
            "wayfarer": "t1",
            "pathfinder": "t1",
            "explorer": "t2",
            "pioneer": "t3",
        }
        sponsors = [
            {
                "disabled": f"disabled_{n}" in request.form,
                "id": int(request.form.get(f"id_{n}")),
                "bucket": request.form.get(f"bucket_{n}")
                or bucket.get(f"type_{n}", "t1"),
                **{x: request.form.get(f"{x}_{n}") or None for x in fields},
            }
            for n in sorted(numbers)
            if request.form.get(f"name_{n}", "").strip()
        ]
        app.data_cache.admin.update_sponsors(sponsors)
        return redirect(url_for("admin.sponsor"))

    return render_template(
        "admin/sponsors.html",
        contents=contents,
        t3=t3,
        t2=t2,
        t1=t1,
    )


@admin_bp.route("/admin/perms", methods=["GET", "POST"])
@admin_only
def perms():
    app = get_app()
    permissions = app.data_cache.admin.get_permissions()

    if request.method == "POST":
        values = [p.strip() for p in request.form.get("perms", "").splitlines()]
        app.data_cache.admin.update_perms(values)
        return redirect(url_for("admin.perms"))

    return render_template(
        "admin/perms.html",
        perms=permissions,
    )
