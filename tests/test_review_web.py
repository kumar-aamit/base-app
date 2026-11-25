import html as htmllib
import re

from fastapi.testclient import TestClient

from baseapp.main import create_app
from tests.test_llm_runner import make_app


def client(tmp_path):
    return TestClient(create_app(make_app(tmp_path)))


def test_root_redirects_to_first_screen(tmp_path):
    r = client(tmp_path).get("/", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/s/triage"


def test_review_page_shows_inputs_examples_and_privacy_note(tmp_path):
    page = htmllib.unescape(client(tmp_path).get("/s/triage").text)
    assert "Triage an alert" in page and 'name="alert"' in page and 'type="file"' in page
    assert "Spray" in page and 'data-example="0"' in page
    assert "What you enter stays in HQ data center" in page


def test_example_run_renders_blocks_sources_and_route(tmp_path):
    frag = htmllib.unescape(client(tmp_path).post("/s/triage/run", data={"example": "0"}).text)
    assert "Likely password spray" in frag
    assert "Block 203.0.113.45 at the VPN gateway" in frag
    assert "vpn.md › Contain" in frag
    assert "Mock answer" in frag and "route" in frag


def test_upload_is_read_as_text(tmp_path):
    files = {"logs": ("vpn.log", b"FAIL x\nFAIL y\nFAIL z\n", "text/plain")}
    r = client(tmp_path).post("/s/triage/run", data={"alert": "spray?"}, files=files)
    assert r.status_code == 200 and "Mock answer for Verdict" in r.text


def test_missing_required_input_is_an_inline_error(tmp_path):
    r = client(tmp_path).post("/s/triage/run", data={})
    assert r.status_code == 200 and "Paste the alert is required" in r.text and "notice-fail" in r.text


def test_json_api_runs_examples(tmp_path):
    r = client(tmp_path).post("/api/screens/triage/run", json={"example": 0})
    body = r.json()
    assert r.status_code == 200 and body["mocked"] is True
    assert body["answer"]["checklist"][0]["source"] == "[1]"
    assert body["sources"][0] == {"n": 1, "source": "vpn.md", "heading": "Contain"}
    assert set(body["timings"]) == {"total_ms", "model_ms"}


def test_json_api_error_is_422_with_message(tmp_path):
    r = client(tmp_path).post("/api/screens/triage/run", json={"inputs": {}})
    assert r.status_code == 422 and r.json()["error"] == "Paste the alert is required"


def test_unknown_screen_is_404(tmp_path):
    assert client(tmp_path).get("/s/nope").status_code == 404


def test_no_external_urls_on_screen_page(tmp_path):
    c = client(tmp_path)
    for body in (c.get("/s/triage").text, c.post("/s/triage/run", data={"example": "0"}).text,
                 c.get("/static/js/review.js").text):
        urls = re.findall(r"https?://[^\s\"')]+", body)
        assert [u for u in urls if not u.startswith("http://www.w3.org/")] == []


def test_broken_screen_file_shows_error_and_keeps_serving(tmp_path):
    settings = make_app(tmp_path)
    (tmp_path / "screens" / "triage.yaml").write_text("layout: assistant\ninputs: []\n")
    c = TestClient(create_app(settings))
    assert c.get("/health").status_code == 200
    page = htmllib.unescape(c.get("/").text)
    assert "app/screens/triage.yaml" in page and "Your app will appear here" in page
