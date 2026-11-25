import asyncio
import json

import httpx
import pytest

from baseapp.config import ModelEndpoint, Settings
from baseapp.llm import ModelError, complete_json
from baseapp.runner import RunError, load_runtime, run_screen

EP = ModelEndpoint("http://m:8000/v1", "nvidia/nemotron-3.5-super")
SCHEMA = {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}


def call(handler, reasoning=True):
    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            return await complete_json(c, EP, None, [{"role": "user", "content": "hi"}], SCHEMA,
                                       reasoning=reasoning, tier="smart")
    return asyncio.run(go())


def reply(content):
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


def test_sends_schema_and_parses_json():
    seen = {}

    def h(req):
        seen.update(json.loads(req.content))
        return reply('{"text": "ok"}')
    answer, ms = call(h, reasoning=False)
    assert answer == {"text": "ok"} and ms >= 0
    assert seen["model"] == "nvidia/nemotron-3.5-super"
    assert seen["response_format"]["json_schema"]["schema"] == SCHEMA
    assert seen["chat_template_kwargs"] == {"enable_thinking": False}


def test_reasoning_on_sends_no_template_switch():
    seen = {}

    def h(req):
        seen.update(json.loads(req.content))
        return reply('{"text": "ok"}')
    call(h)
    assert "chat_template_kwargs" not in seen


def test_strips_code_fences():
    assert call(lambda r: reply('```json\n{"text": "ok"}\n```'))[0] == {"text": "ok"}


def test_http_error_is_readable():
    with pytest.raises(ModelError, match=r"smart model returned HTTP 500"):
        call(lambda r: httpx.Response(500, text="boom"))


def test_not_json_is_readable():
    with pytest.raises(ModelError, match=r"smart model did not return JSON"):
        call(lambda r: reply("Sure! Here is"))


APP_YAML = 'name: Alert Triage\nsite: HQ data center\nscreens: [triage]\n'
SCREEN = """
title: Triage an alert
model: smart
inputs:
  - {name: alert, type: textarea, label: Paste the alert}
  - {name: logs, type: file, optional: true}
knowledge: knowledge/
answer:
  - text: {title: Verdict}
  - checklist: {title: Next steps}
examples:
  - label: Spray
    inputs: {alert: "212 failed VPN logins from 203.0.113.45", logs: data/vpn.log}
    mock:
      text: Likely password spray with one compromised account.
      checklist:
        - {step: Block 203.0.113.45 at the VPN gateway, source: "[1]"}
"""
PROMPT = "Alert:\n{{ alert }}\n{% if logs %}Logs ({{ failed }} failures):\n{{ logs }}{% endif %}"
HOOKS = "def prepare(ctx):\n    return {'failed': ctx.inputs['logs'].count('FAIL')}\n"


def make_app(tmp_path, prompt=PROMPT):
    for d in ("screens", "prompts", "data", "knowledge"):
        (tmp_path / d).mkdir()
    (tmp_path / "app.yaml").write_text(APP_YAML)
    (tmp_path / "screens" / "triage.yaml").write_text(SCREEN)
    (tmp_path / "prompts" / "triage.md").write_text(prompt)
    (tmp_path / "data" / "vpn.log").write_text("FAIL j.ortiz\nFAIL a.chen\nOK j.ortiz\n")
    (tmp_path / "knowledge" / "vpn.md").write_text("# Password spray\n\n## Contain\nBlock the source address at the VPN gateway.\n")
    (tmp_path / "hooks.py").write_text(HOOKS)
    return Settings.from_env({"APP_DIR": str(tmp_path), "LLM_MOCK": "1"})


def run(settings, inputs, example=None):
    rt = load_runtime(settings)

    async def go():
        async with httpx.AsyncClient() as c:
            return await run_screen(rt, rt.screens["triage"], inputs, example, c)
    return asyncio.run(go())


def test_example_run_uses_its_mock_and_builds_the_prompt(tmp_path):
    r = run(make_app(tmp_path), {}, example=0)
    assert r.mocked and r.answer["text"].startswith("Likely password spray")
    assert "212 failed VPN logins" in r.prompt and "Logs (2 failures)" in r.prompt
    assert "[1] vpn.md — Contain" in r.prompt
    assert r.sources[0].heading == "Contain"


def test_typed_input_overrides_example_and_gets_placeholder_answer(tmp_path):
    r = run(make_app(tmp_path), {"alert": "Phishing email reported"})
    assert "Phishing email reported" in r.prompt and "Logs" not in r.prompt
    assert r.answer["text"].startswith("Mock answer")


def test_required_input_missing(tmp_path):
    with pytest.raises(RunError, match=r"Paste the alert is required"):
        run(make_app(tmp_path), {})


def test_undefined_prompt_variable_names_the_file(tmp_path):
    with pytest.raises(RunError, match=r"app/prompts/triage.md: 'severity' is undefined"):
        run(make_app(tmp_path, prompt="{{ alert }} {{ severity }}"), {"alert": "x"})
