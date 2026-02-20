import pymongo

def test_mongodb_ping():
    client = pymongo.MongoClient("mongodb://admin:secret@localhost:27017/", serverSelectionTimeoutMS=3000)
    assert client.admin.command("ping")["ok"] == 1
