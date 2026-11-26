import pytest

from baseapp.blocks import json_schema, placeholder_answer, answer_problems
from baseapp.screens import ScreenError, load_screen

TRIAGE = """
title: Triage an alert
layout: review
model: smart
reasoning: off
inputs:
  - {name: alert, type: textarea, label: Paste the alert}
  - {name: logs, type: file, accept: ".log,.txt,.csv", optional: true}
  - {name: asset, type: select, options: data/assets.csv, optional: true}
knowledge: knowledge/
output: json
answer:
  - score: {title: Severity}
  - text: {title: Verdict}
  - table: {title: Attack techniques, columns: [Technique, ATT&CK ID, Evidence]}
  - checklist: {title: Next steps}
examples:
  - label: Password spray, then a login
    inputs: {alert: "212 failed VPN logins", logs: data/vpn.log}
"""


def app_dir(tmp_path, text=TRIAGE, name="triage"):
    (tmp_path / "screens").mkdir(exist_ok=True)
    (tmp_path / "screens" / f"{name}.yaml").write_text(text)
    (tmp_path / "prompts").mkdir(exist_ok=True)
    (tmp_path / "prompts" / f"{name}.md").write_text("Triage: {{ alert }}")
    (tmp_path / "data").mkdir(exist_ok=True)
    (tmp_path / "data" / "assets.csv").write_text("name,owner\nvpn-gw-01,netops\nhr-db,hr\n")
    (tmp_path / "data" / "vpn.log").write_text("fail\n")
    (tmp_path / "knowledge").mkdir(exist_ok=True)
    return tmp_path


def test_loads_alert_triage(tmp_path):
    s = load_screen(app_dir(tmp_path), "triage")
    assert s.title == "Triage an alert" and s.layout == "review" and s.model == "smart"
    assert s.reasoning is False and s.output == "json"
    assert [i.name for i in s.inputs] == ["alert", "logs", "asset"]
    assert s.inputs[1].label == "Logs" and s.inputs[1].optional
    assert s.inputs[2].choices == ("vpn-gw-01", "hr-db")
    assert [(b.kind, b.key, b.title) for b in s.answer] == [
        ("score", "score", "Severity"), ("text", "text", "Verdict"),
        ("table", "table", "Attack techniques"), ("checklist", "checklist", "Next steps")]
    assert s.answer[2].columns == ("Technique", "ATT&CK ID", "Evidence")
    assert s.examples[0].label == "Password spray, then a login"


def test_bad_input_type_names_field_and_fix(tmp_path):
    text = TRIAGE.replace("type: select", "type: dropdown")
    with pytest.raises(ScreenError, match=r'app/screens/triage.yaml: inputs\[2\].type "dropdown" is not valid; use one of text, textarea, select, number, toggle, file'):
        load_screen(app_dir(tmp_path, text), "triage")


def test_missing_prompt_file(tmp_path):
    d = app_dir(tmp_path)
    (d / "prompts" / "triage.md").unlink()
    with pytest.raises(ScreenError, match=r"app/prompts/triage.md is missing"):
        load_screen(d, "triage")


def test_layout_not_built_yet_says_so(tmp_path):
    with pytest.raises(ScreenError, match=r'layout "assistant" is not available in this platform version; use review'):
        load_screen(app_dir(tmp_path, TRIAGE.replace("layout: review", "layout: assistant")), "triage")


def test_example_input_must_exist(tmp_path):
    text = TRIAGE.replace("alert: \"212", "alrt: \"212")
    with pytest.raises(ScreenError, match=r'examples\[0\].inputs: unknown input "alrt"'):
        load_screen(app_dir(tmp_path, text), "triage")


def confined(tmp_path, value):
    d = tmp_path / "app"
    d.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.md").write_text("# Secret\n\nnot part of the app\n")
    return app_dir(d, TRIAGE.replace("knowledge: knowledge/", f"knowledge: {value}")), outside


def test_knowledge_absolute_path_rejected(tmp_path):
    d, outside = confined(tmp_path, "/etc")
    with pytest.raises(ScreenError, match=r'app/screens/triage.yaml: knowledge: "/etc" is an absolute path; '
                                          r'use a folder inside app/, like knowledge/'):
        load_screen(d, "triage")


def test_knowledge_dotdot_escape_rejected(tmp_path):
    d, outside = confined(tmp_path, "knowledge/../../outside")
    with pytest.raises(ScreenError, match=r'app/screens/triage.yaml: knowledge: "knowledge/../../outside" uses \.\. '
                                          r'to leave app/; use a folder inside app/, like knowledge/'):
        load_screen(d, "triage")


def test_knowledge_app_root_rejected(tmp_path):
    d, outside = confined(tmp_path, "./")
    with pytest.raises(ScreenError, match=r'knowledge: "\./" is app/ itself; use a folder inside app/'):
        load_screen(d, "triage")


def test_knowledge_folder_symlinked_outside_rejected(tmp_path):
    d, outside = confined(tmp_path, "runbooks/")
    (d / "runbooks").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ScreenError, match=r"app/screens/triage.yaml: knowledge: app/runbooks/ is a symlink to "
                                          r".*outside, outside app/; copy the documents into a folder inside app/"):
        load_screen(d, "triage")


def test_knowledge_file_symlinked_outside_rejected(tmp_path):
    d, outside = confined(tmp_path, "knowledge/")
    (d / "knowledge" / "secret.md").symlink_to(outside / "secret.md")
    with pytest.raises(ScreenError, match=r"app/screens/triage.yaml: knowledge: app/knowledge/secret.md is a symlink "
                                          r"to .*secret.md, outside app/; copy the file into app/knowledge/ instead"):
        load_screen(d, "triage")


def test_knowledge_folder_inside_app_allowed_even_through_a_symlink(tmp_path):
    d, outside = confined(tmp_path, "docs/runbooks")
    (d / "knowledge" / "spray.md").write_text("# Password spray\n\n## Contain\n\nBlock the address.\n")
    (d / "docs").mkdir()
    (d / "docs" / "runbooks").symlink_to(d / "knowledge", target_is_directory=True)
    s = load_screen(d, "triage")
    assert s.knowledge == (d / "knowledge").resolve()


def test_duplicate_block_keys_rejected(tmp_path):
    text = TRIAGE.replace("  - checklist: {title: Next steps}", "  - text: {title: Timeline}")
    with pytest.raises(ScreenError, match=r'answer\[3\]: key "text" is used twice; add key: to one of them'):
        load_screen(app_dir(tmp_path, text), "triage")


def test_schema_and_placeholder_agree(tmp_path):
    s = load_screen(app_dir(tmp_path), "triage")
    schema = json_schema(s.answer)
    assert schema["required"] == ["score", "text", "table", "checklist"]
    assert schema["properties"]["table"]["items"]["required"] == ["Technique", "ATT&CK ID", "Evidence"]
    assert answer_problems(s.answer, placeholder_answer(s.answer)) == []


def test_answer_problems_name_the_block():
    from baseapp.screens import AnswerBlock
    blocks = (AnswerBlock("score", "score", "Severity"), AnswerBlock("checklist", "checklist", "Next steps"))
    problems = answer_problems(blocks, {"score": {"value": 140, "label": "High"}})
    assert problems == ["score.value must be 0 to 100", "checklist is missing"]
