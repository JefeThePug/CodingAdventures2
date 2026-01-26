import os

from flask import session

from app.appctx import get_app


def register_globals():
    """Register global Jinja template helpers.
    Attaches utility functions to the Flask application so they can be
    used directly inside Jinja templates.
    """
    app = get_app()

    @app.template_global()
    def obfuscate(year: str, value: str | int) -> str | int:
        """Obfuscate a value using the obfuscation mapping.
        Args:
            value (str | int): The value to obfuscate.
            year (str): Current year
        Returns:
            str | int: The obfuscated value.
        """
        return app.data_cache.admin.html_nums[year][value]

    @app.template_global()
    def obscure_post(value: str | int) -> str:
        """Obscure a challenge number for display in templates.
        Args:
            value (str | int): The number to obfuscate.
        Returns:
            str: The obfuscated number for HTML output.
        """
        if isinstance(value, str):
            value = int(value)
        return app.data_cache.admin.obfuscations[session["year"]][int(value)]

    @app.context_processor
    def inject_css_files() -> dict[str, list[str]]:
        year = app.config["CURRENT_YEAR"]
        return {
            "borders": [f"{y}{p}" for y in range(2025, year + 1) for p in "AB"],
            "css_files": [
                "main",
                # "sponsor",
                # "navbar",
                # "style",
                f"style{session.get('year', year)}",
            ],
        }
