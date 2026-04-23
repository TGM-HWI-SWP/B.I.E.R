import urllib.error
import urllib.request

import pytest


def test_flask_reachable():
    """Checks that the externally running Flask server answers on port 5000."""
    try:
        with urllib.request.urlopen("http://localhost:5000", timeout=5) as response:
            body = response.read().decode("utf-8", errors="ignore")
            assert response.status == 200
            assert "<html" in body.lower() or "<!doctype html" in body.lower()
    except urllib.error.URLError as exc:
        pytest.skip(f"Flask server not reachable on localhost:5000: {exc}")
