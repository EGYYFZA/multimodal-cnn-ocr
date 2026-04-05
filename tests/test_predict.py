import requests

BASE = "http://127.0.0.1:8000"

def test_health():
    r = requests.get(f"{BASE}/api/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True

def test_predict_text_only():
    r = requests.post(f"{BASE}/api/predict", data={"title":"uji", "body":"ini contoh berita untuk diuji"})
    assert r.status_code == 200
    j = r.json()
    assert "label" in j and "prob_hoax" in j
