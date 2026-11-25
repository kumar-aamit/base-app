#!/usr/bin/env bash
# Assemble dist/team-repo/: the files start-lab.sh seeds into every team repo.
# team-repo/ supplies the repo files; platform/ is a read-only copy of baseapp for make dev.
set -euo pipefail

WATCHFILES_VERSION=1.3.0

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${ROOT}/dist/team-repo"

rm -rf "${OUT}"
mkdir -p "${OUT}/platform"
cp -R "${ROOT}/team-repo/." "${OUT}/"
cp -R "${ROOT}/baseapp" "${OUT}/platform/baseapp"
find "${OUT}/platform" -name '__pycache__' -type d -prune -exec rm -rf {} +
cp "${ROOT}/requirements.txt" "${OUT}/platform/requirements.txt"
printf -- '-r requirements.txt\nwatchfiles==%s\n' "${WATCHFILES_VERSION}" > "${OUT}/platform/requirements-dev.txt"

echo "Wrote ${OUT} ($(find "${OUT}" -type f | wc -l | tr -d ' ') files)"
