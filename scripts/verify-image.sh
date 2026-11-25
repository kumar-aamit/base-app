#!/usr/bin/env bash
# Run IMAGE the way OpenShift's restricted-v2 SCC does (read-only root, random
# UID in group 0, writable /tmp) and fail unless it is ready in under 1 s and
# idles under 64 MiB.
set -euo pipefail

IMAGE="${1:?usage: verify-image.sh IMAGE}"
PORT="${PORT:-18742}"
NAME="verify-base-app-$$"

podman image exists "${IMAGE}" || { echo "image not found: ${IMAGE}" >&2; exit 1; }
trap 'podman rm -f "${NAME}" >/dev/null 2>&1 || true' EXIT

podman run -d --name "${NAME}" --read-only --tmpfs /tmp --user 1000770000:0 \
  -p "${PORT}:8742" -e LLM_MOCK=1 "${IMAGE}" >/dev/null

started="$(podman inspect -f '{{.State.StartedAt}}' "${NAME}")"

python3 - "${PORT}" "${started}" <<'PY'
import sys, time, urllib.request
from datetime import datetime, timezone

port, started = sys.argv[1], sys.argv[2]
# podman prints e.g. 2026-11-25 02:10:01.123456789 +0000 UTC
stamp = started.split(" +")[0]
date, clock = stamp.split(" ")
clock = clock[:15]
t0 = datetime.fromisoformat(f"{date}T{clock}").replace(tzinfo=timezone.utc).timestamp()
deadline = time.time() + 10
while time.time() < deadline:
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=0.5)
        break
    except OSError:
        time.sleep(0.02)
else:
    sys.exit("not ready within 10 s")
ms = (time.time() - t0) * 1000
print(f"ready in {ms:.0f} ms (container start to first /healthz answer)")
sys.exit(1 if ms >= 1000 else 0)
PY

sleep 5
usage="$(podman stats --no-stream --format '{{.MemUsage}}' "${NAME}")"
python3 - "${usage}" <<'PY'
import re, sys
value, unit = re.match(r"\s*([\d.]+)\s*([kKMG]i?B)", sys.argv[1]).groups()
scale = {"kB": 1e3, "KB": 1e3, "KiB": 1024, "MB": 1e6, "MiB": 1024**2, "GB": 1e9, "GiB": 1024**3}[unit]
mib = float(value) * scale / 1024**2
print(f"idle memory {mib:.1f} MiB ({sys.argv[1].strip()})")
sys.exit(1 if mib >= 64 else 0)
PY
