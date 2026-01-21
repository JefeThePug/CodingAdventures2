from flask import Blueprint, render_template, session

from app.services import get_progress
from app.utils.current_app import get_app

route_bp = Blueprint("routes", __name__)


@route_bp.route("/help")
def how_to() -> str:
    """Render the help page.
    Returns:
        str: Rendered howto.html template with user information.
    """
    user = get_progress()
    return render_template(
        "how_to.html",
        img=user["img"],
        year=session["year"],
    )


@route_bp.route("/champions")
def champions() -> str:
    """Render the champions page.
    Returns:
        str: Rendered champions.html template with user information.
    """
    user = get_progress()

    names, links = [], []
    for champion in get_app().data_cache.progress.get_all_champions():
        names.append(champion["name"])
        links.append(champion["github"])

    return render_template(
        "champions.html",
        img=user["img"],
        year=session["year"],
        champions=names,
        githubs=links,
    )


@route_bp.route("/gratitude")
def gratitude() -> str:
    """Render the gratitude page.
    Returns:
        str: Rendered gratitude.html template with user information.
    """
    user = get_progress()
    return render_template(
        "gratitude.html",
        img=user["img"],
        year=session["year"],
    )


@route_bp.route("/sponsor")
def sponsor() -> str:
    """Render the sponsor page.
    Returns:
        str: Rendered sponsor.html template with user information.
    """
    user = get_progress()

    t3, t2, t1 = [], [], []
    # FIX!!!!
    for s in get_app().data_cache.get_all_sponsors():
        if s["type"] == "pioneer":
            t3.append()
        elif s["type"] == "explorer":
            t2.append()
        else:
            t1.append()

    return render_template(
        "sponsor.html",
        img=user["img"],
        year=session["year"],
        t3=t3, t2=t2, t1=t1,
    )
