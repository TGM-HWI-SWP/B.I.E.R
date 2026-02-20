import pymongo
import requests

def test_mongodb_ping():
    """MongoDB ist direkt über Port 27017 erreichbar."""
    client = pymongo.MongoClient("mongodb://admin:secret@localhost:27017/", serverSelectionTimeoutMS=3000)
    assert client.admin.command("ping")["ok"] == 1

def test_mongo_express_reachable():
    """Mongo Express Web-UI ist über Port 8081 per HTTP erreichbar."""
    response = requests.get("http://localhost:8081", timeout=5)
    assert response.status_code == 200
