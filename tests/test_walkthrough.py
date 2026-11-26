import re
from pathlib import Path

import pytest

from baseapp import check

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
