from flask import Blueprint, render_template, request, session, flash

from app.appctx import get_app

admin_bp = Blueprint("admin", __name__)

@admin_bp.route("/admin", methods=["GET", "POST"])
def admin():
    return render_template("admin/default.html")

@admin_bp.route("/admin/home")
def admin_home():
    return render_template("admin/home.html")

@admin_bp.route("/admin/discord", methods=["GET", "POST"])
def discord():
    app = get_app()
    years = list(map(str, range(2025, app.config["CURRENT_YEAR"] + 1)))
    selected_year = request.args.get(
        "year",
        request.form.get("year", f"{app.config['CURRENT_YEAR']}")
    )
    channels = {
        "2025": {i: "TEST-2025" for i in range(1, 11)},
        "2026": {i: "TEST-2026" for i in range(1, 11)}
    }
    # flash("Invalid test", "error")

    return render_template(
        "admin/discord.html",
        years=years,
        selected_year=selected_year,
        guild="GUILD",
        role="ROLE",
        channels=channels,
    )

@admin_bp.route("/admin/release", methods=["GET", "POST"])
def release():
    app = get_app()
    years = list(map(str, range(2025, app.config["CURRENT_YEAR"] + 1)))
    releases = {year: 10 for year in years}

    return render_template(
        "admin/release.html",
        years=years,
        release=releases,
    )