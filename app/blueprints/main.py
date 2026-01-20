from flask import Blueprint, Response, redirect, render_template, session, url_for, current_app

from app.services import get_progress

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index() -> Response:
    """Redirect to the index page for the current year or the year in session.
    Returns:
        Response: Rendered redirect to current year.
    """
    session.setdefault("year", "2025")
    return redirect(url_for("main.release", year=session["year"]))


@main_bp.route("/<int:year>")
def release(year) -> str:
    """Render the index page for a specific year with user progress and release number.
    Returns:
        str: Rendered index.html template.
    """
    session["year"] = f"{year}"
    user = get_progress()
    return render_template(
        "index.html",
        img=user["img"],
        year=session["year"],
        rockets=user["rockets"],
        num=current_app.data_cache.release,
    )
