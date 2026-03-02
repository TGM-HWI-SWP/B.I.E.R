"""Shared utility helpers for the backend service layer."""

import datetime

def get_current_timestamp() -> str:
    """Return the current UTC timestamp as an ISO 8601 string with a Z suffix.

    Returns:
        A timestamp string in the format '2025-01-01T12:00:00.000000Z'.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    # Remove the '+00:00' offset added by timezone-aware datetime and replace with 'Z'.
    iso_string = now.isoformat()
    if iso_string.endswith("+00:00"):
        iso_string = iso_string[:-6]
    return iso_string + "Z"
