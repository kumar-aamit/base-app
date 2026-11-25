import html as htmllib
import re

from fastapi.testclient import TestClient

from baseapp.config import Settings
from baseapp.main import create_app


def client(tmp_path, yaml_text=None, **env):
    if yaml_text is not None:
        (tmp_path / "app.yaml").write_text(yaml_text)
    return TestClient(create_app(Settings.from_env({"APP_DIR": str(tmp_path), "LLM_MOCK": "1", **env})))


def test_health_both_paths(tmp_path):
    c = client(tmp_path)
    assert c.get("/health").json() == {"status": "ok"}
    assert c.get("/healthz").json() == {"status": "ok"}


def test_docs_off_openapi_on(tmp_path):
    c = client(tmp_path)
    assert c.get("/docs").status_code == 404
    assert c.get("/openapi.json").status_code == 200


def test_placeholder_shows_brand_badge_and_site(tmp_path):
    html = client(tmp_path, 'name: Alert Triage\nbrand: "#1D4ED8"\nsite: HQ data center\n').get("/").text
    assert "Alert Triage" in html and "#1D4ED8" in html
    assert "Air-gap capable" in html and "Data stays in HQ data center" in html


def test_bad_config_still_serves_and_reports(tmp_path):
    c = client(tmp_path, "brand: blue\n", APP_COMMIT="abc1234def")
    assert c.get("/health").status_code == 200
    assert 'brand "blue" is not valid' in htmllib.unescape(c.get("/").text)
    v = c.get("/api/version").json()
    assert v["commit"] == "abc1234def" and v["config_error"].startswith("app/app.yaml:")


def test_checks_json_and_fragment(tmp_path):
    c = client(tmp_path, APP_COMMIT="abc1234def")
    rows = c.get("/api/checks").json()
    assert [r["name"] for r in rows] == ["App", "Fast model", "Smart model"]
    assert rows[0]["detail"] == "running abc1234"
    assert rows[1]["ok"] is None and rows[1]["detail"] == "skipped: mock mode"
    frag = c.get("/api/checks", headers={"HX-Request": "true"}).text
    assert "<html" not in frag
    assert frag.count("check-skip") == 2 and frag.count("check-ok") == 1


def test_page_declares_inline_favicon(tmp_path):
    assert '<link rel="icon" href="data:,">' in client(tmp_path).get("/").text


def test_no_external_urls_in_pages_or_css(tmp_path):
    c = client(tmp_path)
    bodies = [c.get("/").text, c.get("/static/css/base.css").text]
    for body in bodies:
        urls = re.findall(r"https?://[^\s\"')]+", body)
        assert [u for u in urls if not u.startswith("http://www.w3.org/")] == []
