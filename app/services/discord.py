import requests
from flask import current_app

def exchange_code(code: str) -> dict:
    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": current_app.config["DISCORD_REDIRECT_URI"],
        "client_id": current_app.config["DISCORD_CLIENT_ID"],
        "client_secret": current_app.config["DISCORD_CLIENT_SECRET"],
    }

    response = requests.post(
        "https://discord.com/api/oauth2/token",
        data=token_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    return response.json()