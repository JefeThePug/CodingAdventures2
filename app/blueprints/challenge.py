import requests
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


def fix_static(txt: str) -> str:
    """Replace the "__STATIC__" placeholder in the html
    with the path to the static directory.
    Args:
        txt (str): Raw html text
    Returns:
        str: html text with the correct path for images and files
    """
    return txt.replace("__STATIC__", url_for("static", filename=""))


@challenge_bp.route("/challenge/<year>/<obs_num>", methods=["GET", "POST"])
def challenge(year: str, obs_num: str) -> str | Response:
    """Render the challenge page for a specific challenge week number.
    Args:
        year (str): The desired year.
        obs_num (str): The obfuscated challenge number.
    Returns:
        str: Rendered challenge.html template or error message.
        Response: redirect to the challenge page on correct guess.
    """
    session["year"] = year
    app = get_app()
    num = app.data_cache.admin.html_nums[year][obs_num]
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
                    redirect(url_for("challenge.challenge", year=year, obs_num=obs_num))
                )
                if cookie:
                    resp.set_cookie(cookie, f"{num}{'AB'[n]}")
                return resp
            else:
                error = "Incorrect. Please try again."

    user = get_progress()
    progress = user["progress"][f"c{num}"]
    html = app.data_cache.html.html[year][num]
    try:
        a = {k: fix_static(v) for k, v in html[1].items()}
        b = {k: fix_static(v) for k, v in html[2].items()}
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


@challenge_bp.route("/access", methods=["POST"])
def access() -> str | tuple[str, int]:
    """Grant access to a user and assign roles in Discord.

    Returns:
        str: Rendered link_complete.html template or error message.
        tuple[str, int]: Error message with HTTP status code.
    """
    app = get_app()
    bot_token = app.config["DISCORD_BOT_TOKEN"]
    year = session["year"]
    if not bot_token:
        return "Error: Bot token not found", 500

    num = app.data_cache.admin.obfuscations[year][f"{request.form.get('num')}"]

    guild_id = app.data_cache.admin.discord_ids["0"]["guild"]
    user_id = session["user_data"]["id"]
    channel_id = app.data_cache.admin.discord_ids[year][f"{num}"]
    print(
        f"{app.data_cache.admin.discord_ids[year]=} {num=} {app.data_cache.admin.discord_ids[year][f'{num}']=}"
    )
    verified_role = app.data_cache.admin.discord_ids["0"]["verified"]

    headers = {"Authorization": f"Bot {bot_token}", "Content-Type": "application/json"}
    url = f"https://discord.com/api/v9/guilds/{guild_id}/members/{user_id}"
    response = requests.get(url, headers=headers)

    # User is not a member of the guild, add them
    if response.status_code == 404:
        payload = {"access_token": session["token"]}
        try:
            response = requests.put(url, headers=headers, json=payload)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
            return f"Error: Failed to assign role: {response.text}", 400
        url += f"/roles/{verified_role}"
        try:
            response = requests.put(url, headers=headers)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            return f"Error: {e}", 400
        else:
            if response.status_code != 204:
                return f"Error: Failed to assign role: {response.text}", 400

    content = (
        f"<@{user_id}> solved week {num}! If you'd like, "
        "please share how you arrived at the correct answer!"
    )
    url = f"https://discord.com/api/v9/channels/{channel_id}/thread-members/{user_id}"
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
        try:
            response = requests.post(url, headers=headers, json={"content": content})
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            return f"Error: {e}", 400
        else:
            if response.status_code != 200:
                return f"Error: Failed to send message: {response.text}", 400

    user = get_progress()
    egg = app.data_cache.html.html[year][num]["ee"]

    return render_template(
        "link_complete.html",
        img=user["img"],
        num=num,
        guild=guild_id,
        channel=channel_id,
        egg=egg,
    )
