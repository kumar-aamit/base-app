#!/usr/bin/env bash
# Fetch htmx, fonts and icons from the npm registry into baseapp/static/vendor/.
# Run on a developer machine only; the outputs are committed so image builds
# and running pods never reach the internet.
set -euo pipefail

HTMX_VERSION=2.0.11
FONT_VERSION=5.3.0
LUCIDE_VERSION=1.79.0
ICONS=(shield circle-check triangle-alert wifi-off server monitor-smartphone)

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENDOR="${ROOT}/baseapp/static/vendor"
TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT

fetch() {  # fetch <npm package> <version> <dest dir>
  local name="$1" version="$2" dest="$3" base
  base="$(basename "${name}")"
  mkdir -p "${dest}"
  curl -fsSL "https://registry.npmjs.org/${name}/-/${base}-${version}.tgz" | tar -xz -C "${dest}"
}

fetch htmx.org "${HTMX_VERSION}" "${TMP}/htmx"
fetch @fontsource/atkinson-hyperlegible-next "${FONT_VERSION}" "${TMP}/next"
fetch @fontsource/atkinson-hyperlegible-mono "${FONT_VERSION}" "${TMP}/mono"
fetch lucide-static "${LUCIDE_VERSION}" "${TMP}/lucide"

mkdir -p "${VENDOR}/fonts" "${VENDOR}/icons"
cp "${TMP}/htmx/package/dist/htmx.min.js" "${VENDOR}/htmx.min.js"
for w in 400 700; do
  cp "${TMP}/next/package/files/atkinson-hyperlegible-next-latin-${w}-normal.woff2" "${VENDOR}/fonts/"
  cp "${TMP}/mono/package/files/atkinson-hyperlegible-mono-latin-${w}-normal.woff2" "${VENDOR}/fonts/"
done
for icon in "${ICONS[@]}"; do
  cp "${TMP}/lucide/package/icons/${icon}.svg" "${VENDOR}/icons/"
done
cp "${TMP}/lucide/package/LICENSE" "${VENDOR}/icons/LICENSE"

echo "Vendored htmx ${HTMX_VERSION}, Atkinson Hyperlegible ${FONT_VERSION}, lucide ${LUCIDE_VERSION}"
