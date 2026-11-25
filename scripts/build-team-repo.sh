#!/usr/bin/env bash
# Assemble dist/team-repo/: the files start-lab.sh seeds into every team repo.
# This repo's root is laid out as a team repo; SEED lists the parts teams get. Everything
# else here (Containerfile, tests, scripts, docs, the paper) is base-app tooling.
set -euo pipefail

SEED=(AGENTS.md Dockerfile Makefile team.env.example .gitignore .gitea app catalog examples skills platform)

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${ROOT}/dist/team-repo"

rm -rf "${OUT}"
mkdir -p "${OUT}"
for path in "${SEED[@]}"; do
  cp -R "${ROOT}/${path}" "${OUT}/${path}"
done
find "${OUT}" -name '__pycache__' -type d -prune -exec rm -rf {} +
PYTHONPATH="${ROOT}/platform" "${PYTHON:-python3.12}" -m baseapp.pin "${OUT}/platform/baseapp" > "${OUT}/platform/PIN"

echo "Wrote ${OUT} ($(find "${OUT}" -type f | wc -l | tr -d ' ') files)"
