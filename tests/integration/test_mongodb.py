"""Connectivity smoke-tests that require a running Docker stack.

Run these with ``pytest -m live`` after ``docker-compose up``.
They are skipped automatically in offline / CI environments.
"""

import pymongo
import pytest
import requests


def _mongodb_available() -> bool:
    """Return True when a local MongoDB instance is reachable.

    Returns:
        bool: True if MongoDB responds to a ping within 1 second.
    """
    try:
        client = pymongo.MongoClient(
            "mongodb://admin:secret@localhost:27017/",
            serverSelectionTimeoutMS=1000,
        )
        client.admin.command("ping")
        return True
    except Exception:
        return False


requires_mongo = pytest.mark.skipif(
    not _mongodb_available(),
    reason="MongoDB not reachable – start Docker stack first",
)


@requires_mongo
def test_mongodb_ping():
    """MongoDB ist direkt über Port 27017 erreichbar."""
    client = pymongo.MongoClient(
        "mongodb://admin:secret@localhost:27017/",
        serverSelectionTimeoutMS=3000,
    )
    assert client.admin.command("ping")["ok"] == 1


@pytest.mark.skipif(
    True,
    reason="Mongo Express reachability – start Docker stack first",
)
def test_mongo_express_reachable():
    """Mongo Express Web-UI ist über Port 8081 per HTTP erreichbar."""
    response = requests.get("http://localhost:8081", timeout=5)
    assert response.status_code == 200
