import html as htmllib
import json
import re
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from baseapp.config import Settings, app_version
from baseapp.main import create_app
from baseapp.screens import ScreenError, load_screen

ROOT = Path(__file__).resolve().parent.parent
NETCONF = ROOT / "examples" / "netconf-guard" / "app"


def client(app_dir, **env):
    settings = Settings.from_env({"APP_DIR": str(app_dir), "LLM_MOCK": "1", "SITE_NAME": "dCloud San Jose", **env})
    return TestClient(create_app(settings))


def text(r) -> str:
    return htmllib.unescape(r.text)


def test_version_comes_from_app_version_then_the_openshift_build_number():
    assert app_version({"APP_VERSION": "7"}) == "7"
    assert app_version({"OPENSHIFT_BUILD_NAME": "user-7-12"}) == "12"
    assert app_version({}) == "dev"


def test_status_page_has_ten_tiles_with_meanings_and_no_header_badge(tmp_path):
    page = text(client(tmp_path).get("/status"))
    names = re.findall(r'<span class="tile-name">([^<]+)</span>', page)
    assert names == ["App", "Fast model", "Smart model", "Knowledge", "Air-gapped", "Private data",
                     "Token cost", "Data residency", "Under load", "Model version"]
    assert page.count('role="tooltip"') == 10
    assert "Air-gap capable" not in page and "status-link" not in page


def test_model_tile_lists_both_models_with_precision(tmp_path):
    page = text(client(tmp_path, LLM_FAST_MODEL="meta-llama/Llama-3.1-8B-Instruct",
                       LLM_SMART_MODEL="nvidia/nemotron-3.5-super",
                       LLM_FAST_PRECISION="FP8", LLM_SMART_PRECISION="NVFP4").get("/status"))
    assert "nemotron-3.5-super · NVFP4\nLlama-3.1-8B-Instruct · FP8" in page


def test_model_tile_claims_no_precision_unless_set(tmp_path):
    page = text(client(tmp_path, LLM_FAST_MODEL="meta-llama/Llama-3.1-8B-Instruct",
                       LLM_SMART_MODEL="nvidia/nemotron-3.5-super").get("/status"))
    assert "nemotron-3.5-super\nLlama-3.1-8B-Instruct" in page
    assert "NVFP4" not in page and "FP8" not in page


def test_footer_shows_app_version_build_and_platform(tmp_path):
    page = text(client(tmp_path, APP_COMMIT="7c20d4b1aa", OPENSHIFT_BUILD_NAME="user-7-3").get("/"))
    footer = page.split('<footer class="app-footer">')[1]
    assert "Mock App <strong>v3</strong>" in footer and "<code>7c20d4b</code>" in footer
    assert "deployed" in footer and "base-app 0.2.0" in footer
    assert "OpenShift" not in footer


def test_ask_and_load_in_mock_mode_say_no_model_was_called(tmp_path):
    c = client(tmp_path)
    assert "Mock answer: no model was called" in c.post("/status/ask/fast").text
    assert "Mock mode: no model was called" in c.post("/status/load").text
    assert c.post("/status/ask/huge").status_code == 404


def fake_models(handler):
    def make(tmp_path):
        settings = Settings.from_env({"APP_DIR": str(tmp_path), "LLM_FAST_URL": "http://fast/v1",
                                      "LLM_FAST_MODEL": "meta-llama/Llama-3.1-8B-Instruct",
                                      "LLM_SMART_URL": "http://smart/v1", "LLM_SMART_MODEL": "nvidia/nemotron-3.5-super"})
        app = create_app(settings)
        app.state.http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        return app, TestClient(app)
    return make


def reply(content, tokens=40):
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}],
                                      "usage": {"total_tokens": tokens}})


def test_ask_names_the_model_counts_tokens_and_costs_nothing(tmp_path):
    seen = []

    def handler(req):
        seen.append(json.loads(req.content))
        return reply("<think>hmm</think>Failed login, medium severity.", tokens=52)
    app, c = fake_models(handler)(tmp_path)
    frag = text(c.post("/status/ask/fast"))
    assert "Failed login, medium severity." in frag and "<think>" not in frag
    assert "Llama-3.1-8B-Instruct" in frag and "52 tokens" in frag and "$0" in frag
    assert seen[0]["model"] == "meta-llama/Llama-3.1-8B-Instruct"
    assert app.state.stats.tokens == 52


def test_load_sends_ten_requests_to_the_fast_model(tmp_path):
    models = []

    def handler(req):
        models.append(json.loads(req.content)["model"])
        return reply("medium", tokens=10)
    app, c = fake_models(handler)(tmp_path)
    frag = text(c.post("/status/load"))
    assert models == ["meta-llama/Llama-3.1-8B-Instruct"] * 10
    assert frag.count("<li>") == 10 and "All 10 answered by Llama-3.1-8B-Instruct" in frag
    assert app.state.stats.tokens == 100 and len(app.state.stats.load_ms) == 10


def test_netconf_screen_shows_its_chips_and_a_status_link():
    page = text(client(NETCONF).get("/s/review"))
    chips = re.findall(r"<span>([^<]+)</span>\s*<strong>([^<]+)</strong>", page)
    assert [c[0] for c in chips] == ["Air-gapped", "Configs stored", "Reviews", "Last review", "Model", "Standard"]
    assert ("Reviews", "0 · $0") in chips and ("Standard", "1 doc · 6 sections") in chips
    assert '<a class="status-link" href="/status">' in page and "Network Config Review" in page


def test_a_run_updates_the_chips_and_colors_severity_and_score():
    c = client(NETCONF)
    frag = text(c.post("/s/review/run", data={"example": "0"}))
    assert 'id="status-chips" aria-label="Status" hx-swap-oob="true"' in frag
    assert re.search(r"<span>Reviews</span>\s*<strong>1 · \$0</strong>", frag)
    assert '<span class="sev sev-high">High</span>' in frag and '<span class="sev sev-low">Low</span>' in frag
    assert 'class="score score-high"' in frag
    assert '<td class="mono">transport input ssh</td>' in frag


def test_screens_without_status_get_the_default_chips(tmp_path):
    from tests.test_llm_runner import make_app
    page = text(TestClient(create_app(make_app(tmp_path))).get("/s/triage"))
    labels = re.findall(r"<span>([^<]+)</span>\s*<strong>", page)
    assert labels == ["Air-gapped", "Data stored", "Runs", "Last answer", "Model", "Knowledge"]


def screen(tmp_path, extra: str):
    (tmp_path / "prompts").mkdir(exist_ok=True)
    (tmp_path / "screens").mkdir(exist_ok=True)
    (tmp_path / "prompts" / "s.md").write_text("{{ q }}")
    (tmp_path / "screens" / "s.yaml").write_text(
        "inputs: [{name: q, type: text}]\nanswer: [text]\n" + extra)
    return load_screen(tmp_path, "s")


def test_status_field_is_validated_with_fixes(tmp_path):
    assert screen(tmp_path, "status: off\n").status == ()
    assert [c.label for c in screen(tmp_path, "status: [airgap, {runs: Reviews}]\n").status] == ["", "Reviews"]
    with pytest.raises(ScreenError, match='chip "speed" is not valid; use one of airgap'):
        screen(tmp_path, "status: [speed]\n")
    with pytest.raises(ScreenError, match="no knowledge: folder"):
        screen(tmp_path, "status: [knowledge]\n")
    with pytest.raises(ScreenError, match="lists a chip twice"):
        screen(tmp_path, "status: [runs, runs]\n")


def test_higher_is_only_for_scores(tmp_path):
    screen(tmp_path, "")
    path = tmp_path / "screens" / "s.yaml"
    path.write_text("inputs: [{name: q, type: text}]\nanswer: [{score: {higher: worse}}]\n")
    assert load_screen(tmp_path, "s").answer[0].higher == "worse"
    path.write_text("inputs: [{name: q, type: text}]\nanswer: [{text: {higher: worse}}]\n")
    with pytest.raises(ScreenError, match="higher: worse or higher: better"):
        load_screen(tmp_path, "s")


def test_no_external_urls_on_status_page_or_fragments(tmp_path):
    c = client(tmp_path)
    for body in (c.get("/status").text, c.get("/status/tiles").text, c.post("/status/ask/smart").text,
                 c.get("/static/css/base.css").text):
        urls = re.findall(r"https?://[^\s\"')]+", body)
        assert [u for u in urls if not u.startswith("http://www.w3.org/")] == []
