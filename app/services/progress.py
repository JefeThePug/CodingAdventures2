from typing import TypedDict

from flask import session, request

from app.appctx import get_app


class ProgressPayload(TypedDict):
    """Structure returned by get_progress() for templates and handlers."""

    id: str | None
    img: str
    progress: dict[str, list[bool]]
    rockets: list[list[bool]]


def sync_progress(user_id: str) -> None:
    """Synchronize the user's progress from the database into the session.
    Loads the user's progress via the DataCache and stores it in the Flask
    session so request handlers and templates can access it without
    additional database queries.
    Args:
        user_id (str): The Discord user ID.
    """
    session["progress"] = get_app().data_cache.progress.load_progress(user_id)


def set_progress(challenge_num: int, progress: int) -> str | None:
    """Update the progress for the current user in the database.
    Args:
        challenge_num (int): The challenge number.
        progress (int): The specific progress index (0 or 1).
    Returns:
        str | None: The serialized progress if user is not logged in, otherwise None.
    """
    if "user_data" in session:
        # Change database and update Data Cache

        get_app().data_cache.update_progress(
            session["user_data"]["id"],
            challenge_num,
            progress,
        )
        sync_progress(session["user_data"]["id"])
    else:
        # Alter Browser Cookies
        return get_app().serializer.dumps(f"{challenge_num}{'AB'[progress]}")


def get_progress() -> ProgressPayload:
    """Retrieve the progress of the user.
    Returns:
        dict: A dictionary containing user progress and session information.
    """
    if "user_data" in session:
        # Retrieve information from Flask session and Data Cache
        session["progress"] = get_app().data_cache.progress.load_progress(
            session["user_data"]["id"]
        )
        return {
            "id": session["user_data"]["id"],
            "img": session["user_data"]["img"],
            "progress": session["progress"],
            "rockets": [session["progress"][f"c{i}"] for i in range(1, 11)],
        }
    # Else, retrieve information from Browser Cookies
    cookies = [*request.cookies.keys()]
    s = [get_app().serializer.loads(x) for x in cookies if len(x) > 40]
    rockets = [[f"{n}{p}" in s for p in "AB"] for n in range(1, 11)]
    progress = {f"c{i}": r for i, r in enumerate(rockets, 1)}
    return {
        "id": None,
        "img": "no_img.png",
        "progress": progress,
        "rockets": rockets,
    }
