"""Flask HTTP adapter – concrete implementation of the HttpResponsePort contract."""

from bierapp.contracts.http_port import HttpResponsePort

class FlaskHttpAdapter(HttpResponsePort):
    """Builds standardised JSON response bodies for Flask route handlers."""

    def success(self, data: dict, status: int = 200) -> tuple:
        """Build a successful JSON response body.

        Args:
            data: The response payload to include under the 'data' key.
            status: HTTP status code. Defaults to 200.

        Returns:
            A tuple of (response_dict, status_code) ready for Flask to serialise.
        """
        response_body = {
            "status": "ok",
            "data": data,
        }
        return response_body, status

    def error(self, message: str, status: int = 400) -> tuple:
        """Build an error JSON response body.

        Args:
            message: Human-readable description of what went wrong.
            status: HTTP status code. Defaults to 400.

        Returns:
            A tuple of (response_dict, status_code) ready for Flask to serialise.
        """
        response_body = {
            "status": "error",
            "message": message,
        }
        return response_body, status
