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
        "year", request.form.get("year", f"{app.config['CURRENT_YEAR']}")
    )
    channels = {
        "2025": {i: "TEST-2025" for i in range(1, 11)},
        "2026": {i: "TEST-2026" for i in range(1, 11)},
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


@admin_bp.route("/admin/solutions", methods=["GET", "POST"])
def solutions():
    app = get_app()
    years = list(map(str, range(2025, app.config["CURRENT_YEAR"] + 1)))
    selected_year = request.args.get(
        "year", request.form.get("year", f"{app.config['CURRENT_YEAR']}")
    )
    print(request.args.get("year", "no args"), request.form.get("year", "no form"))

    solution_list = {
        "2025": {i: [f"25 test-{i}0", f"25 test-{i}1"] for i in range(1, 11)},
        "2026": {i: [f"26 test-{i}0", f"26 test-{i}1"] for i in range(1, 11)},
    }

    return render_template(
        "admin/solutions.html",
        years=years,
        selected_year=selected_year,
        solutions=solution_list,
    )


@admin_bp.route("/admin/html", methods=["GET", "POST"])
def html():
    app = get_app()
    years = list(map(str, range(2025, app.config["CURRENT_YEAR"] + 1)))
    print(request.args.get("year", "no args"), request.form.get("year", "no form"))
    selected_year = request.args.get(
        "year", request.form.get("year", f"{app.config['CURRENT_YEAR']}")
    )
    selected_week = int(request.args.get("week", request.form.get("week", 1)))

    data = {
        "2025": {
            i: {
                part: {
                    "title": f"2025.{i}.{part} title",
                    "content": f"2025.{i}.{part} content",
                    "instructions": f"2025.{i}.{part} instructions",
                    "input": f"2025.{i}.{part} input",
                    "form": f"2025.{i}.{part} form",
                    "solution": f"2025.{i}.{part} solution",
                }
                for part in range(1, 3)
            }
            for i in range(1, 11)
        },
        "2026": {
            i: {
                part: {
                    "title": f"2026.{i}.{part} title",
                    "content": f"2026.{i}.{part} content",
                    "instructions": f"2026.{i}.{part} instructions",
                    "input": f"2026.{i}.{part} input",
                    "form": f"2026.{i}.{part} form",
                    "solution": f"2026.{i}.{part} solution",
                }
                for part in range(1, 3)
            }
            for i in range(1, 11)
        },
    }

    return render_template(
        "admin/html.html",
        years=years,
        selected_year=selected_year,
        selected_week=selected_week,
        data=data,
    )


@admin_bp.route("/admin/perms", methods=["GET", "POST"])
def perms():
    app = get_app()
    perm_list = [f"TESTING{i}" for i in range(__import__("random").randint(3, 6))]

    return render_template(
        "admin/perms.html",
        perms=perm_list,
    )
