from flask import current_app


def register_globals():
    """Register global Jinja template helpers.
    Attaches utility functions to the Flask application so they can be
    used directly inside Jinja templates.
    """

    @current_app.template_global()
    def obfuscate(value: str | int) -> str | int:
        """Obfuscate a value using the obfuscation mapping.
        Args:
            value (str | int): The value to obfuscate.
        Returns:
            str | int: The obfuscated value.
        """
        return current_app.data_cache.html_nums[value]

    @current_app.template_global()
    def obscure_post(value: str | int) -> str:
        """Obscure a challenge number for display in templates.
        Args:
            value (str | int): The number to obfuscate.
        Returns:
            str: The obfuscated number for HTML output.
        """
        if isinstance(value, str):
            value = int(value)
        return current_app.data_cache.obfuscations[int(value)]
