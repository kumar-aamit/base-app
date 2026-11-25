from pathlib import Path

import pytest

from baseapp import check

ROOT = Path(__file__).resolve().parent.parent
APPS = [
    "team-repo/app",
    "docs/walkthrough/alert-triage/step-1-build/app",
    "docs/walkthrough/alert-triage/step-2-ground/app",
    "team-repo/examples/alert-triage/app",
]


@pytest.mark.parametrize("app", APPS)
def test_every_walkthrough_step_passes_make_check(app, capsys):
    code = check.main(app_dir=ROOT / app)
    assert code == 0, capsys.readouterr().out
