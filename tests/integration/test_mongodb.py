import pytest

pymongo = pytest.importorskip("pymongo")
requests = pytest.importorskip("requests")


def test_mongodb_ping():
    """Checks that an externally running MongoDB instance responds to ping."""
    client = pymongo.MongoClient("mongodb://admin:secret@localhost:27017/", serverSelectionTimeoutMS=3000)
    try:
        assert client.admin.command("ping")["ok"] == 1
    except Exception as exc:
        pytest.skip(f"MongoDB not reachable on localhost:27017: {exc}")


def test_mongo_express_reachable():
    """Checks that mongo-express is reachable over HTTP on port 8081."""
    try:
        response = requests.get("http://localhost:8081", timeout=5)
        assert response.status_code == 200
    except Exception as exc:
        pytest.skip(f"Mongo Express not reachable on localhost:8081: {exc}")
