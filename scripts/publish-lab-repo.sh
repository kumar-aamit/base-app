#!/usr/bin/env bash
# Rebuild dist/lab-repo/ and publish it to the lab starter repo as one commit on top of the last.
# The starter repo is generated output: never commit to it directly; change base-app and run this.
# Publish from a clean main so every starter commit names the base-app commit it came from.
set -euo pipefail

STARTER_REPO="${STARTER_REPO:-https://github.com/kumar-aamit/openclaw-lab-starter.git}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

die() { echo "publish-lab-repo: $*" >&2; exit 1; }

cd "${ROOT}"
branch="$(git branch --show-current)"
[[ "${branch}" == main || "${ALLOW_BRANCH:-0}" == 1 ]] || die "on ${branch}; publish from main (ALLOW_BRANCH=1 to override)"
read -r -a seed <<< "$(sed -n 's/^SEED=(\(.*\))$/\1/p' scripts/build-lab-repo.sh)"
[[ -z "$(git status --porcelain -- "${seed[@]}")" ]] || die "seeded paths have uncommitted changes; commit them first"
sha="$(git rev-parse --short HEAD)"

scripts/build-lab-repo.sh

work="$(mktemp -d)"
trap 'rm -rf "${work}"' EXIT
git clone -q --depth 1 "${STARTER_REPO}" "${work}" 2>/dev/null
cd "${work}"
git rm -rq --ignore-unmatch .
cp -R "${ROOT}/dist/lab-repo/." .
git add -A
if git diff --cached --quiet; then
  echo "Starter already matches base-app ${branch} (${sha}); nothing to publish."
  exit 0
fi
git diff --cached --stat | tail -n 1
git commit -q -m "Seeded lab repo from base-app ${branch} (${sha})"
git push -q origin HEAD:main
echo "Published base-app ${branch} (${sha}) to ${STARTER_REPO}"
