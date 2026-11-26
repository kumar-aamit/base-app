import re
from pathlib import Path

import pytest

from baseapp import check
from baseapp.start import use_cases

ROOT = Path(__file__).resolve().parent.parent
APPS = [
    "app",
    "docs/walkthrough/alert-triage/step-1-build/app",
    "docs/walkthrough/alert-triage/step-2-ground/app",
    "examples/alert-triage/app",
] + sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / "docs" / "gallery").glob("*/app"))


@pytest.mark.parametrize("app", APPS)
def test_every_walkthrough_step_passes_make_check(app, capsys):
    code = check.main(app_dir=ROOT / app)
    assert code == 0, capsys.readouterr().out


def prompts(path: str) -> list[str]:
    return re.findall(r"```text\n(.*?)```", (ROOT / path).read_text(), re.S)


def test_guide_sends_the_briefs_three_prompts_word_for_word():
    brief = prompts("catalog/it-alert-triage.md")
    assert len(brief) == 3 and prompts("GUIDE.md") == brief


def test_start_page_offers_the_briefs_three_prompts_word_for_word():
    def words(text):
        return " ".join(text.split())
    triage = next(c for c in use_cases() if c.id == "triage")
    assert [s.name for s in triage.steps] == ["Build", "Ground it", "Shape the answer"]
    assert [words(s.prompt) for s in triage.steps] == [words(p) for p in prompts("catalog/it-alert-triage.md")]
