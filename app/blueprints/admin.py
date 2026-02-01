from flask import Blueprint, render_template, request, session, flash, url_for, redirect

from app.appctx import get_app

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin", methods=["GET", "POST"])
def admin():
    return render_template("admin/default.html")


@admin_bp.route("/admin/home")
def admin_home():
    return render_template("admin/home.html")


@admin_bp.route("/admin/release", methods=["GET", "POST"])
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
            selected_year: {f"{i}": request.form.get(f"c{i}", "").strip() for i in range(1, 11)},
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
def html():
    app = get_app()
    years = list(map(str, range(2025, app.config["CURRENT_YEAR"] + 1)))
    selected_year = request.args.get(
        "year", request.form.get("year", f"{app.config['CURRENT_YEAR']}")
    )
    selected_week = int(request.args.get("week", request.form.get("week", 1)))
    focus = app.data_cache.html.html[selected_year][selected_week]
    data = {part: focus[part] for part in range(1, 3)}

    return render_template(
        "admin/html.html",
        years=years,
        selected_year=selected_year,
        selected_week=selected_week,
        data=data,
    )


@admin_bp.route("/admin/solutions", methods=["GET", "POST"])
def solutions():
    app = get_app()
    years = list(map(str, range(2025, app.config["CURRENT_YEAR"] + 1)))
    selected_year = request.args.get(
        "year", request.form.get("year", f"{app.config['CURRENT_YEAR']}")
    )
    solution_list = {y: app.data_cache.html.solutions[y] for y in years}

    return render_template(
        "admin/solutions.html",
        years=years,
        selected_year=selected_year,
        solutions=solution_list,
    )


@admin_bp.route("/admin/users", methods=["GET", "POST"])
def user():
    app = get_app()
    years = list(map(str, range(2025, app.config["CURRENT_YEAR"] + 1)))
    selected_year = request.args.get(
        "year", request.form.get("year", f"{app.config['CURRENT_YEAR']}")
    )
    users = app.data_cache.get_glance(selected_year)

    return render_template(
        "admin/users.html",
        years=years,
        selected_year=selected_year,
        users=users,
    )


@admin_bp.route("/admin/sponsors", methods=["GET", "POST"])
def sponsor():
    app = get_app()
    contents = [
        ["name", "type", "website"],
        ["name", "type", "website", "image"],
        ["name", "type", "website", "image", "blurb"]
    ]
    t1, t2, t3 = app.data_cache.admin.get_all_sponsors(True)

    return render_template(
        "admin/sponsors.html",
        contents=contents,
        t3=t3,
        t2=t2,
        t1=t1,
    )



@admin_bp.route("/admin/perms", methods=["GET", "POST"])
def perms():
    app = get_app()
    permissions = app.data_cache.admin.permissions
    
    if request.method == "POST":
        values = [p.strip() for p in request.form.get("perms", "").splitlines()]
        app.data_cache.admin.update_perms(values)
        return redirect(url_for("admin.perms"))

    return render_template(
        "admin/perms.html",
        perms=permissions,
    )
