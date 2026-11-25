import pytest

from baseapp.files import extract_text
from baseapp.hookrunner import Ctx, HookError, load_hooks, run_prepare
from baseapp.knowledge import KnowledgeIndex

RUNBOOK = """# VPN password spray

## Detect
Many failed VPN logins from one source address across several users.

## Contain
Block the source address at the VPN gateway. Force a password reset for any account that later signed in.

# Phishing

## Triage
Pull the message headers and check the sender domain.
"""


def test_search_returns_the_matching_section(tmp_path):
    (tmp_path / "runbook.md").write_text(RUNBOOK)
    (tmp_path / "notes.txt").write_text("Printer on floor 3 jams often.\n\nCall facilities.")
    idx = KnowledgeIndex.build(tmp_path)
    hits = idx.search("block source address after failed vpn logins and a password reset", k=2)
    assert hits[0].source == "runbook.md" and hits[0].heading == "Contain"
    assert "Block the source address" in hits[0].text
    assert all(h.source != "notes.txt" for h in hits)


def test_search_with_no_overlap_returns_nothing(tmp_path):
    (tmp_path / "runbook.md").write_text(RUNBOOK)
    assert KnowledgeIndex.build(tmp_path).search("zebra giraffe") == []


def test_sections_are_found_by_their_document_title(tmp_path):
    (tmp_path / "spray.md").write_text("# Password spray\n\n## Escalate\nCall the incident lead.\n")
    (tmp_path / "beacon.md").write_text("# Malware beacon\n\n## Escalate\nIsolate the host.\n")
    hits = KnowledgeIndex.build(tmp_path).search("password spray", k=4)
    assert [(p.source, p.heading) for p in hits] == [("spray.md", "Escalate")]


def test_extract_text_from_log_and_csv():
    assert extract_text("a.log", b"line one\nline two\n") == "line one\nline two\n"
    assert extract_text("a.csv", "user,ok\nj.ortiz,yes\n".encode()) .startswith("user,ok")


def test_extract_text_rejects_unknown_type():
    with pytest.raises(ValueError, match=r"\.exe files are not supported; use .txt, .log, .csv or .pdf"):
        extract_text("x.exe", b"MZ")


def test_hooks_add_values_and_read_data(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "assets.csv").write_text("name,owner\nvpn-gw-01,netops\n")
    (tmp_path / "hooks.py").write_text(
        "def prepare(ctx):\n"
        "    owners = {r['name']: r['owner'] for r in ctx.data('assets.csv')}\n"
        "    return {'owner': owners.get(ctx.inputs['asset'], 'unknown'),\n"
        "            'lines': len(ctx.inputs['logs'].splitlines())}\n")
    hooks = load_hooks(tmp_path)
    out = run_prepare(hooks, Ctx(app_dir=tmp_path, inputs={"asset": "vpn-gw-01", "logs": "a\nb\n"}))
    assert out == {"owner": "netops", "lines": 2}


def test_no_hooks_file_means_no_extra_values(tmp_path):
    assert run_prepare(load_hooks(tmp_path), Ctx(app_dir=tmp_path, inputs={})) == {}


def test_hook_that_crashes_names_the_file_and_line(tmp_path):
    (tmp_path / "hooks.py").write_text("def prepare(ctx):\n    return 1 / 0\n")
    with pytest.raises(HookError, match=r"app/hooks.py line 2: ZeroDivisionError"):
        run_prepare(load_hooks(tmp_path), Ctx(app_dir=tmp_path, inputs={}))


def test_hook_must_return_a_dict(tmp_path):
    (tmp_path / "hooks.py").write_text("def prepare(ctx):\n    return [1]\n")
    with pytest.raises(HookError, match=r"prepare\(ctx\) must return a dict"):
        run_prepare(load_hooks(tmp_path), Ctx(app_dir=tmp_path, inputs={}))


def test_data_cannot_escape_the_data_folder(tmp_path):
    (tmp_path / "data").mkdir()
    with pytest.raises(HookError, match=r"ctx.data"):
        Ctx(app_dir=tmp_path, inputs={}).data("../hooks.py")
