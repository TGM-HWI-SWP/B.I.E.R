import urllib.request

def test_flask_reachable():
    with urllib.request.urlopen("http://localhost:5000", timeout=5) as r:
        assert r.status == 200
