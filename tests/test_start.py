import html as htmllib
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from baseapp.config import Settings
from baseapp.main import create_app
from baseapp.start import use_cases

ROOT = Path(__file__).resolve().parent.parent
WALK = "docs/walkthrough/alert-triage"


def client(app_dir, **env):
    return TestClient(create_app(Settings.from_env({"APP_DIR": str(app_dir), "LLM_MOCK": "1", **env})))


def page(app_dir, url="/", **env):
    return htmllib.unescape(client(app_dir, **env).get(url).text)


def test_empty_app_opens_on_the_start_page_with_prompt_1(tmp_path):
    html = page(tmp_path)
    assert "What do you want to build?" in html
    assert "Build an alert triage app for our HQ security team." in html
    assert "Copy prompt 1" in html and 'aria-current="step"' in html


def test_start_offers_all_ten_use_cases(tmp_path):
    html = page(tmp_path, "/start")
    assert len(use_cases()) == 10
    for case in use_cases():
        assert f'href="/start?case={case.id}"' in html


def test_case_and_step_come_from_the_query(tmp_path):
    html = page(tmp_path, "/start?case=triage&step=2")
    assert "Add our incident runbooks" in html and "Copy prompt 2" in html
    assert "Send prompt 1 first" in html
    config = page(tmp_path, "/start?case=config")
    assert "NOC network engineers" in config and "Copy prompt" in config and "Copy prompt 1" not in config


def test_unknown_case_and_step_fall_back_to_the_first_prompt(tmp_path):
    html = page(tmp_path, "/start?case=nope&step=x")
    assert "Build an alert triage app" in html and "Copy prompt 1" in html


def test_own_idea_gets_a_text_box_and_every_block_to_preview(tmp_path):
    html = page(tmp_path, "/start?case=own")
    assert '<textarea id="prompt"' in html
    for kind in ("score", "text", "table", "checklist"):
        assert f'data-kind="{kind}"' in html


@pytest.mark.parametrize("app, done", [
    (f"{WALK}/step-1-build/app", 1),
    (f"{WALK}/step-2-ground/app", 2),
    ("examples/alert-triage/app", 3),
])
def test_steps_tick_from_what_the_app_already_has(app, done):
    html = page(ROOT / app, "/start")
    assert len(re.findall(r'class="step step-done', html)) == done
    assert f"Copy prompt {min(done + 1, 3)}" in html


def test_lab_user_shows_in_the_header_only_when_set(tmp_path):
    assert '<span class="lab-user">· user-7</span>' in page(tmp_path, LAB_USER="user-7")
    assert 'class="lab-user"' not in page(tmp_path)


def test_built_app_links_back_to_the_start_page():
    assert '<a href="/start">Start page</a>' in page(ROOT / "examples/alert-triage/app", "/s/triage")


def test_status_fragment_shows_mock_mode_in_words(tmp_path):
    frag = client(tmp_path).get("/api/checks?view=status", headers={"HX-Request": "true"}).text
    assert "<html" not in frag and frag.count('<span class="status-detail">: skipped: mock mode</span>') == 2


def test_start_page_and_script_have_no_external_urls(tmp_path):
    c = client(tmp_path)
    for url in ("/start?case=own", "/start?case=clause", "/static/js/start.js"):
        urls = re.findall(r"https?://[^\s\"')]+", c.get(url).text)
        assert [u for u in urls if not u.startswith("http://www.w3.org/")] == []
