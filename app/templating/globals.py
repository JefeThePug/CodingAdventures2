from flask import current_app


def register():
    @current_app.template_global()
    def obfuscate(value: str | int) -> str | int:
        """Obfuscate a value using the obfuscation database.
        Args:
            value (str | int): The value to obfuscate.
        Returns:
            str | int: The obfuscated value.
        """
        return current_app.data_cache.html_nums[value]

    @current_app.template_global()
    def obscure_post(value: str | int) -> str:
        """Obscures week number using Data Cache (from database)
        Args:
            value (str | int): The number to obfuscate.
        Returns:
            str: The obfuscated number to pass to the HTML.
        """
        if isinstance(value, str):
            value = int(value)
        return current_app.data_cache.obfuscations[int(value)]
