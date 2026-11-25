import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE_APP_ONLY = {".dockerignore", "Containerfile", "base-app-paper.md", "docs", "pyproject.toml",
                 "requirements-test.txt", "scripts", "tests"}


def seed_list() -> set[str]:
    script = (ROOT / "scripts" / "build-team-repo.sh").read_text()
    return set(re.search(r"^SEED=\((.*)\)$", script, re.M).group(1).split())


def test_every_top_level_path_is_seeded_or_base_app_only():
    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    top = {line.split("/")[0] for line in tracked.splitlines()}
    seed = seed_list()
    assert not seed & BASE_APP_ONLY
    assert top - seed - BASE_APP_ONLY == set(), "add new top-level paths to SEED or BASE_APP_ONLY"
    assert seed - top == set(), "SEED lists paths that do not exist"
