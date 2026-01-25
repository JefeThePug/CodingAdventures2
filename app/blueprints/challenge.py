from flask import (
    Blueprint,
    render_template,
    Response,
    request,
    make_response,
    redirect,
    url_for,
    session,
)

from app.appctx import get_app
from app.services import get_progress, set_progress

challenge_bp = Blueprint("challenge", __name__)


@challenge_bp.route("/challenge/<year>/<num>", methods=["GET", "POST"])
def challenge(year: str, num: str) -> str | Response:
    """Render the challenge page for a specific challenge week number.
    Args:
        year (str): The desired year.
        num (str): The challenge number.
    Returns:
        str: Rendered challenge.html template or error message.
        Response: redirect to the challenge page on correct guess.
    """
    session["year"] = year
    app = get_app()
    num = app.data_cache.admin.html_nums[year][num]
    error = None

    if request.method == "POST":
        guesses = [request.form.get(f"answer{i}", None) for i in (1, 2)]
        solutions = app.data_cache.html.solutions[year][num]
        for n, guess in enumerate(guesses):
            if (
                guess
                and guess.replace("_", " ").upper().strip() == solutions[f"part{n + 1}"]
            ):
                cookie = set_progress(num, n)
                resp = make_response(
                    redirect(
                        url_for(
                            "get_challenge",
                            num=app.data_cache.admin.html_nums[year][num],
                        )
                    )
                )
                if cookie:
                    resp.set_cookie(cookie, f"{num}{'AB'[n]}")
                return resp
            else:
                error = "Incorrect. Please try again."

    user = get_progress()
    progress = user["progress"][f"c{num}"]
    try:
        a = {
            k: v.replace("__STATIC__", url_for("static", filename=""))
            for k, v in app.data_cache.html.html[year][num][1].items()
        }
        b = {
            k: v.replace("__STATIC__", url_for("static", filename=""))
            for k, v in app.data_cache.html.html[year][num][2].items()
        }
    except KeyError:
        return redirect(url_for("index"))

    params = {
        "img": user["img"],
        "year": session["year"],
        "num": f"{num}",
        "a": a,
        "b": b,
        "sol1": a["solution"] if progress[0] else a["form"],
        "sol2": b["solution"] if progress[1] else b["form"],
        "part_two": progress[0],
        "done": progress[1] and "user_data" in session,
        "error": error,
    }
    return render_template("challenge.html", **params)
