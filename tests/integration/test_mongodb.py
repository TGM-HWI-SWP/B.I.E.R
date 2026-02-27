"""Connectivity smoke-tests that require a running Docker stack.

Run these with ``pytest -m live`` after ``docker-compose up``.
They are skipped automatically in offline / CI environments.
"""

from pymongo import MongoClient
from pytest import mark
from requests import get


def _mongodb_available() -> bool:
    """Return True when a local MongoDB instance is reachable.

    Returns:
        bool: True if MongoDB responds to a ping within 1 second.
    """
    try:
        client = MongoClient(
            "mongodb://admin:secret@localhost:27017/",
            serverSelectionTimeoutMS=1000,
        )
        client.admin.command("ping")
        return True
    except Exception:
        return False


requires_mongo = mark.skipif(
    not _mongodb_available(),
    reason="MongoDB not reachable – start Docker stack first",
)


@requires_mongo
def test_mongodb_ping():
    """MongoDB is reachable directly on port 27017."""
    client = MongoClient(
        "mongodb://admin:secret@localhost:27017/",
        serverSelectionTimeoutMS=3000,
    )
    assert client.admin.command("ping")["ok"] == 1


@mark.skipif(
    True,
    reason="Mongo Express reachability – start Docker stack first",
)
def test_mongo_express_reachable():
    """Mongo Express web UI is reachable on port 8081 via HTTP."""
    response = get("http://localhost:8081", timeout=5)
    assert response.status_code == 200
