import json

import httpx
from fastapi.testclient import TestClient

from baseapp import check, smoke
from baseapp.main import create_app
from baseapp.pin import tree_hash
from tests.test_llm_runner import make_app


def run_check(tmp_path, capsys, **kw):
    code = check.main(app_dir=tmp_path, **kw)
    return code, capsys.readouterr().out


def test_good_app_passes(tmp_path, capsys):
    make_app(tmp_path)
    code, out = run_check(tmp_path, capsys)
    assert code == 0, out
    assert "ok    triage: example \"Spray\"" in out and "All checks passed" in out


def test_low_contrast_brand_fails(tmp_path, capsys):
    make_app(tmp_path)
    app_yaml = tmp_path / "app.yaml"
    app_yaml.write_text(app_yaml.read_text().replace("#17202B", "#FFD54F") if "#17202B" in app_yaml.read_text()
                        else app_yaml.read_text() + "brand: \"#FFD54F\"\n")
    code, out = run_check(tmp_path, capsys)
    assert code == 1 and "brand #FFD54F" in out and "4.5" in out


def test_external_url_fails(tmp_path, capsys):
    make_app(tmp_path)
    p = tmp_path / "prompts" / "triage.md"
    p.write_text(p.read_text() + "\nSee https://example.com/help\n")
    code, out = run_check(tmp_path, capsys)
    assert code == 1 and "app/prompts/triage.md line" in out and "https://example.com/help" in out


def test_non_stdlib_hook_import_fails(tmp_path, capsys):
    make_app(tmp_path)
    (tmp_path / "hooks.py").write_text("import requests\n\ndef prepare(ctx):\n    return {}\n")
    code, out = run_check(tmp_path, capsys)
    assert code == 1 and "app/hooks.py line 1: requests is not in the Python standard library" in out


def test_screen_without_examples_fails(tmp_path, capsys):
    make_app(tmp_path)
    s = tmp_path / "screens" / "triage.yaml"
    text = s.read_text()
    s.write_text(text[: text.index("examples:")])
    code, out = run_check(tmp_path, capsys)
    assert code == 1 and "triage: add at least one example" in out


def test_broken_yaml_reports_and_stops(tmp_path, capsys):
    make_app(tmp_path)
    (tmp_path / "screens" / "triage.yaml").write_text("title: [\n")
    code, out = run_check(tmp_path, capsys)
    assert code == 1 and "app/screens/triage.yaml" in out


def test_mock_citing_a_passage_the_search_did_not_find_fails(tmp_path, capsys):
    make_app(tmp_path)
    s = tmp_path / "screens" / "triage.yaml"
    s.write_text(s.read_text().replace('source: "[1]"', 'source: "[3]"'))
    code, out = run_check(tmp_path, capsys)
    assert code == 1 and "mock cites [3] but the knowledge search found 1 passage(s)" in out


def test_pin_mismatch_fails(tmp_path, capsys):
    (tmp_path / "app").mkdir()
    make_app(tmp_path / "app")
    platform = tmp_path / "platform"
    (platform / "baseapp").mkdir(parents=True)
    (platform / "baseapp" / "x.py").write_text("a = 1\n")
    (platform / "PIN").write_text(tree_hash(platform / "baseapp") + "\n")
    assert run_check(tmp_path / "app", capsys, platform_dir=platform)[0] == 0
    (platform / "baseapp" / "x.py").write_text("a = 2\n")
    code, out = run_check(tmp_path / "app", capsys, platform_dir=platform)
    assert code == 1 and "platform/ was changed" in out


def test_missing_pin_skips_the_platform_comparison(tmp_path, capsys):
    (tmp_path / "app").mkdir()
    make_app(tmp_path / "app")
    (tmp_path / "platform" / "baseapp").mkdir(parents=True)
    code, out = run_check(tmp_path / "app", capsys, platform_dir=tmp_path / "platform")
    assert code == 0 and "skip  platform/PIN not found" in out


def test_smoke_runs_every_example(tmp_path, capsys):
    tc = TestClient(create_app(make_app(tmp_path)))

    def fetch(method, url, body=None):
        r = tc.request(method, url.replace("https://team.example", ""), json=body)
        return r.status_code, r.json()

    code = smoke.main(url="https://team.example", fetch=fetch)
    out = capsys.readouterr().out
    assert code == 0, out
    assert "triage" in out and "Spray" in out and "mock" in out


def test_smoke_reports_errors(capsys):
    def fetch(method, url, body=None):
        if url.endswith("/api/screens"):
            return 200, [{"name": "triage", "title": "T", "examples": ["A"]}]
        return 422, {"error": "the smart model is unreachable"}

    assert smoke.main(url="https://x", fetch=fetch) == 1
    assert "the smart model is unreachable" in capsys.readouterr().out


def test_api_screens_lists_examples(tmp_path):
    tc = TestClient(create_app(make_app(tmp_path)))
    assert tc.get("/api/screens").json() == [{"name": "triage", "title": "Triage an alert", "examples": ["Spray"]}]
