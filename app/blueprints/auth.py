import os
from urllib.parse import urlencode

import requests
from flask import (
    Blueprint,
    Response,
    redirect,
    render_template,
    session,
    url_for,
    request,
)

from app.services import get_progress, exchange_code, sync_progress
from app.appctx import get_app, exception, warning

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/pre-login")
def pre_login() -> str:
    """Render the pre-login page.
    Returns:
        str: Rendered login template with user image.
    """
    user = get_progress()
    template = "logout.html" if "user_data" in session else "login.html"
    return render_template(template, img=user["img"], year=session["year"])


@auth_bp.route("/login")
def login() -> Response:
    """Redirect the user to Discord's OAuth2 authorization page.
    Returns:
        Response: Redirect to Discord authorization URL.
    """
    params = {
        "client_id": os.getenv("DISCORD_CLIENT_ID"),
        "redirect_uri": os.getenv("DISCORD_REDIRECT_URI"),
        "response_type": "code",
        "scope": "identify guilds.members.read guilds.join",
    }
    return redirect(f"https://discord.com/api/oauth2/authorize?{urlencode(params)}")


@auth_bp.route("/callback")
def callback() -> Response | tuple[str, int]:
    """Handle the callback from Discord after user authorization.
    Returns:
        Response: Redirect to the index page or error message.
        tuple[str, int]: Error message with HTTP status code 400.
    """
    if request.args.get("error"):
        exception(f"Request Error (/callback): {request.args}")
        return redirect(url_for("main.index"))

    if not (code := request.args.get("code")):
        return "Error: No code provided", 400

    token_response = exchange_code(code)
    token = token_response.get("access_token")
    if not token:
        warning(f"Token exchange failed: {token_response}")
        return "Error: No token received", 400

    session["token"] = token

    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get("https://discord.com/api/users/@me", headers=headers)
    if response.status_code != 200:
        return "Error: No Response", 400

    if not (user_data := response.json()):
        return "Error: No user data received", 400
    session["user_data"] = user_data

    # Get Discord profile picture for user
    user_id = user_data["id"]
    avatar_hash = user_data["avatar"]
    avatar_url = "images/no_img.png"
    if avatar_hash:
        file_type = ["png", "gif"][avatar_hash.startswith("a_")]
        avatar_url = (
            f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.{file_type}"
        )
    session["user_data"]["img"] = avatar_url

    # Add to database if not present
    progress = get_app().data_cache.load_progress(session["year"], user_id)
    if progress is None:
        added = get_app().data_cache.add_user(
            session["user_data"]["id"], session["user_data"]["username"]
        )
        if not added:
            return redirect(url_for("logout"))
    sync_progress(session["year"], user_id)

    return redirect(url_for("main.index"))


@auth_bp.route("/logout")
def logout() -> Response:
    """Log out the user by clearing the session.
    Returns:
        Response: Redirect to the index page.
    """
    session.clear()
    return redirect(url_for("main.index"))
