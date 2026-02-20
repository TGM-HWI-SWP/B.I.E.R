import urllib.request

def test_gradio_reachable():
    with urllib.request.urlopen("http://localhost:7860", timeout=5) as r:
        assert r.status == 200
