#!/usr/bin/env bash
# Assemble dist/lab-repo/: the files start-lab.sh seeds into every lab user's repo.
# This repo's root is laid out as a lab user's repo; SEED lists the parts each user gets. Everything
# else here (Containerfile, tests, scripts, docs, the paper) is base-app tooling.
set -euo pipefail

SEED=(GUIDE.md guide-images AGENTS.md Dockerfile Makefile lab.env.example .gitignore .gitea app catalog examples skills platform)

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${ROOT}/dist/lab-repo"

rm -rf "${OUT}"
mkdir -p "${OUT}"
for path in "${SEED[@]}"; do
  cp -R "${ROOT}/${path}" "${OUT}/${path}"
done
find "${OUT}" -name '__pycache__' -type d -prune -exec rm -rf {} +
PYTHONPATH="${ROOT}/platform" "${PYTHON:-python3.12}" -m baseapp.pin "${OUT}/platform/baseapp" > "${OUT}/platform/PIN"

echo "Wrote ${OUT} ($(find "${OUT}" -type f | wc -l | tr -d ' ') files)"
