# base-app Phase 1: Skeleton to Cluster — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A team's repo, seeded by `start-lab.sh`, builds FROM a base-app image and serves a branded placeholder page with live model health checks, through the existing Gitea Actions → OpenShift pipeline.

**Architecture:** A Python package, `baseapp`, is a FastAPI app factory that reads env settings and the team's `app/app.yaml`. A base image holds the package and its virtualenv; each team image adds only `app/`. The existing `openshift-automation` bootstrap gains a `base-app` BuildConfig, and the team BuildConfig overrides its `FROM` with that image.

**Tech Stack:** Python 3.12, FastAPI, uvicorn, Jinja2, htmx, httpx, PyYAML, pytest; `ubi9/python-312` and `ubi9/python-312-minimal`; podman locally; OpenShift BuildConfig (Docker strategy, binary source).

**Spec:** `base-app/base-app-paper.md`. Roadmap: `base-app/docs/superpowers/plans/2026-11-25-base-app-roadmap.md`.

## Global Constraints

- Python 3.12. Runtime dependencies are pinned with `==` in `requirements.txt`; phase 1 uses only `fastapi`, `uvicorn`, `jinja2`, `httpx`, `pyyaml` (pin each to its latest stable release at execution time). `pytest` lives in `requirements-dev.txt` and never enters the image.
- The import name is `baseapp`. Never name a Python package `platform`: it shadows the standard library module that uvicorn and httpx import. The team repo's `platform/` folder holds `baseapp/` inside it.
- Nothing loads from the internet: htmx, fonts and icons are committed under `baseapp/static/vendor/`. FastAPI runs with `docs_url=None, redoc_url=None`; `/openapi.json` stays.
- Port `8742` (`APP_PORT`). `GET /health` and `GET /healthz` both answer `{"status": "ok"}` without calling a model.
- Pods: arbitrary UID in group 0, read-only root filesystem, `emptyDir` at `/tmp`, one uvicorn worker. Requests `cpu: 25m, memory: 64Mi`; limits `cpu: 500m, memory: 256Mi`.
- Base image: two-stage build, virtualenv built in `registry.access.redhat.com/ubi9/python-312`, copied into `registry.access.redhat.com/ubi9/python-312-minimal`.
- The team build file is named `Dockerfile` (existing BuildConfigs use `dockerfilePath: Dockerfile`). The paper's "Containerfile" means this file.
- Env vars, exactly: `LLM_FAST_URL`, `LLM_FAST_MODEL`, `LLM_SMART_URL`, `LLM_SMART_MODEL`, `LLM_API_KEY` (optional), `LLM_MOCK` (`1` = no GPU), `SITE_NAME` (default `dCloud lab`). Plus platform-internal `APP_DIR`, `APP_PORT`, `APP_COMMIT`.
- Badge text is exactly `Air-gap capable`. No copy claims the site is air-gapped or compares with cloud services.
- Colors: ground `#ECEFF3`, panels `#FFFFFF`, ink `#17202B`, verified `#0E7A5F`, check failed `#A85B00`. Every status pairs its color with an icon. Fonts: Atkinson Hyperlegible Next and Atkinson Hyperlegible Mono.

## Review Focus

1. **A model endpoint is down, slow or serves a different model name.** The placeholder still renders at once; that check shows failed with the reason (`timeout after 3 s`, `HTTP 503`, `model nvidia/x not served`); `/health` stays 200. → tests in Task 3 and Task 4.
2. **`app/app.yaml` is missing, empty, malformed or has a bad field.** Missing or empty gives the default placeholder. Malformed YAML or a bad field still starts the app; the page shows the error naming file, line and field, and `/api/version` reports it in `config_error`. → tests in Task 2 and Task 4.
3. **Read-only root filesystem with an arbitrary UID.** Anything that writes outside `/tmp` (bytecode, temp files) crashes the pod. → Task 5 runs the image with `--read-only --tmpfs /tmp --user 1000770000:0`.
4. **External URLs in served HTML or CSS.** Any `http://` or `https://` in a page or stylesheet fails, except SVG namespace URIs (`http://www.w3.org/2000/svg`). → test in Task 4.
5. **Endpoint URLs written with a trailing slash, and an empty API key.** `http://h:8000/v1/` and `http://h:8000/v1` behave the same; an empty `LLM_API_KEY` sends no `Authorization` header. → tests in Task 1 and Task 3.

---

## File Structure

```text
base-app/                              git repo (new)
├── base-app-paper.md                  spec
├── requirements.txt                   runtime pins (copied into the image)
├── requirements-dev.txt               -r requirements.txt, pytest
├── pyproject.toml                     pytest config only (pythonpath = ["."], testpaths = ["tests"])
├── Containerfile                      base image
├── .dockerignore                      excludes tests/, docs/, dist/, .venv/
├── baseapp/
│   ├── __init__.py                    __version__ = "0.1.0"
│   ├── __main__.py                    python -m baseapp → uvicorn on APP_PORT
│   ├── config.py                      Settings, ModelEndpoint
│   ├── appspec.py                     AppSpec, AppSpecError, load_app_spec
│   ├── health.py                      CheckResult, check_model, run_checks
│   ├── main.py                        create_app, module-level app
│   ├── wait.py                        python -m baseapp.wait (make wait)
│   ├── templates/{base,placeholder}.html, templates/partials/checks.html
│   └── static/{css/base.css, vendor/htmx.min.js, vendor/fonts/*.woff2, vendor/icons/*.svg}
├── scripts/
│   ├── vendor-assets.sh               one-time fetch; results are committed
│   ├── build-team-repo.sh         assembles dist/team-repo/
│   └── verify-image.sh                read-only, arbitrary-UID, startup and memory check
├── team-repo/                         files seeded into every team repo
│   ├── Dockerfile, Makefile, team.env.example, .gitignore
│   ├── app/app.yaml
│   └── .gitea/workflows/build-deploy-openshift.yml
└── tests/

openclaw-demo/ (modified in Task 7)
├── start-lab.sh
└── openshift-automation/{team.env.example, scripts/*.sh, templates/*.yaml}
```

---

### Task 1: Repo scaffold and settings

**Files:**
- Create: `requirements.txt`, `requirements-dev.txt`, `pyproject.toml`, `.gitignore`, `baseapp/__init__.py`, `baseapp/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces:
  - `ModelEndpoint(url: str, model: str)`, a frozen dataclass; `url` has no trailing slash; `configured: bool` property is true when both fields are non-empty.
  - `Settings`, a frozen dataclass: `app_dir: Path`, `port: int`, `commit: str`, `site_name: str`, `mock: bool`, `api_key: str | None`, `fast: ModelEndpoint`, `smart: ModelEndpoint`.
  - `Settings.from_env(env: Mapping[str, str] = os.environ) -> Settings`. Defaults: `APP_DIR=/opt/app-root/app`, `APP_PORT=8742`, `APP_COMMIT=dev`, `SITE_NAME=dCloud lab`, `LLM_MOCK=0`. An empty `LLM_API_KEY` becomes `None`.

- [ ] **Step 1: Create the repo**

```bash
cd /Users/amitkumar/Documents/demo-guide/base-app
git init -b main
uv venv --python 3.12 .venv && source .venv/bin/activate
```

Write `requirements.txt` (five pins), `requirements-dev.txt`, `pyproject.toml`, and a `.gitignore` listing `.venv/`, `__pycache__/`, `dist/`. Run `uv pip install -r requirements-dev.txt`.

- [ ] **Step 2: Write the failing tests**

```python
from pathlib import Path
from baseapp.config import Settings

def test_defaults():
    s = Settings.from_env({})
    assert s.app_dir == Path("/opt/app-root/app")
    assert s.port == 8742 and s.commit == "dev" and s.site_name == "dCloud lab"
    assert s.mock is False and s.api_key is None
    assert not s.fast.configured and not s.smart.configured

def test_reads_endpoints_and_strips_trailing_slash():
    s = Settings.from_env({
        "LLM_SMART_URL": "http://nemotron-super.models.svc:8000/v1/",
        "LLM_SMART_MODEL": "nvidia/nemotron-3.5-super",
        "LLM_MOCK": "1", "LLM_API_KEY": "", "APP_COMMIT": "abc123",
    })
    assert s.smart.url == "http://nemotron-super.models.svc:8000/v1"
    assert s.smart.configured and s.mock is True
    assert s.api_key is None and s.commit == "abc123"
```

- [ ] **Step 3: Run to verify they fail**

Run: `pytest tests/test_config.py -v` — Expected: FAIL, `ModuleNotFoundError: baseapp.config`.

- [ ] **Step 4: Implement `Settings.from_env` in `baseapp/config.py`**

- [ ] **Step 5: Run to verify they pass**

Run: `pytest tests/test_config.py -v` — Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: scaffold baseapp with env settings"
```

---

### Task 2: Load `app/app.yaml`

**Files:**
- Create: `baseapp/appspec.py`
- Test: `tests/test_appspec.py`

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces:
  - `AppSpec`, a frozen dataclass: `name: str = "Team app"`, `mark: str = ""`, `brand: str = "#17202B"`, `site: str | None = None`, `screens: tuple[str, ...] = ()`. Property `mark_letter: str` returns `mark` if it is one letter, else the first letter of `name`; property `mark_icon: str | None` returns `mark` if it names an icon in `baseapp/static/vendor/icons/`.
  - `AppSpecError(Exception)`; `str(err)` reads `app/app.yaml: <where>: <problem>; <fix>`.
  - `load_app_spec(app_dir: Path) -> AppSpec`. Missing file or an empty document gives `AppSpec()`. Validation in phase 1: `name` is a string of 1–40 characters; `brand` matches `^#[0-9A-Fa-f]{6}$`; `mark` is one letter or a known icon name; `screens` is a list of strings; unknown top-level keys are an error.

- [ ] **Step 1: Write the failing tests**

```python
import pytest
from baseapp.appspec import AppSpec, AppSpecError, load_app_spec

def write(tmp_path, text):
    (tmp_path / "app.yaml").write_text(text)
    return tmp_path

def test_missing_file_gives_placeholder_defaults(tmp_path):
    assert load_app_spec(tmp_path) == AppSpec()

def test_empty_file_gives_defaults(tmp_path):
    assert load_app_spec(write(tmp_path, "")) == AppSpec()

def test_reads_alert_triage(tmp_path):
    spec = load_app_spec(write(tmp_path,
        'name: Alert Triage\nmark: shield\nbrand: "#1D4ED8"\nsite: HQ data center\nscreens: [triage]\n'))
    assert spec.name == "Alert Triage" and spec.brand == "#1D4ED8"
    assert spec.site == "HQ data center" and spec.screens == ("triage",)
    assert spec.mark_icon == "shield"

def test_malformed_yaml_names_the_line(tmp_path):
    with pytest.raises(AppSpecError, match=r"app/app.yaml: line 2"):
        load_app_spec(write(tmp_path, "name: A\nbrand: [\n"))

def test_bad_brand_names_field_and_fix(tmp_path):
    with pytest.raises(AppSpecError, match=r'brand "blue" is not valid; use a hex color like "#1D4ED8"'):
        load_app_spec(write(tmp_path, "brand: blue\n"))

def test_unknown_key_is_an_error(tmp_path):
    with pytest.raises(AppSpecError, match=r'unknown field "colour"'):
        load_app_spec(write(tmp_path, "colour: red\n"))
```

`shield` must exist as `baseapp/static/vendor/icons/shield.svg` for the third test; create a placeholder SVG there now. Task 4 replaces it with the vendored icon.

- [ ] **Step 2: Run to verify they fail**

Run: `pytest tests/test_appspec.py -v` — Expected: FAIL, `ModuleNotFoundError`.

- [ ] **Step 3: Implement `load_app_spec` in `baseapp/appspec.py`**

Use `yaml.safe_load`; on `yaml.MarkedYAMLError` report `problem_mark.line + 1`.

- [ ] **Step 4: Run to verify they pass**

Run: `pytest tests/test_appspec.py -v` — Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: load and validate app.yaml"
```

---

### Task 3: Model health checks

**Files:**
- Create: `baseapp/health.py`
- Test: `tests/test_health.py`

**Interfaces:**
- Consumes: `ModelEndpoint`, `Settings` (Task 1).
- Produces:
  - `CheckResult`, a frozen dataclass: `name: str`, `ok: bool`, `detail: str`, `ms: int | None`.
  - `async check_model(name: str, endpoint: ModelEndpoint, api_key: str | None, client: httpx.AsyncClient, timeout: float = 3.0) -> CheckResult`. Calls `GET {endpoint.url}/models`. `ok` only when the response is 200 and `endpoint.model` is among `data[].id`. Details, exactly: `"<model> answered"`, `"not configured"`, `"timeout after 3 s"`, `"HTTP <code>"`, `"model <model> not served"`, `"unreachable: <exception class>"`.
  - `async run_checks(settings: Settings, client: httpx.AsyncClient) -> list[CheckResult]`, returning `[Fast model, Smart model]` in that order, run concurrently. With `settings.mock`, both are `ok=True, detail="mock mode", ms=None` and no request is sent.

- [ ] **Step 1: Write the failing tests** (use `httpx.MockTransport`; mark async tests with `asyncio.run` inside plain test functions, so no pytest plugin is needed)

```python
import asyncio, httpx
from baseapp.config import ModelEndpoint, Settings
from baseapp.health import check_model, run_checks

EP = ModelEndpoint("http://m:8000/v1", "nvidia/nemotron-3.5-super")

def run(handler, ep=EP, key=None):
    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            return await check_model("Smart model", ep, key, c)
    return asyncio.run(go())

def test_ok_when_model_is_served():
    r = run(lambda req: httpx.Response(200, json={"data": [{"id": EP.model}]}))
    assert r.ok and r.detail == "nvidia/nemotron-3.5-super answered" and r.ms is not None

def test_wrong_model_name():
    r = run(lambda req: httpx.Response(200, json={"data": [{"id": "other"}]}))
    assert not r.ok and r.detail == "model nvidia/nemotron-3.5-super not served"

def test_http_error():
    assert run(lambda req: httpx.Response(503)).detail == "HTTP 503"

def test_timeout():
    def boom(req): raise httpx.ReadTimeout("slow", request=req)
    assert run(boom).detail == "timeout after 3 s"

def test_not_configured_sends_nothing():
    def fail(req): raise AssertionError("no request expected")
    assert run(fail, ep=ModelEndpoint("", "")).detail == "not configured"

def test_auth_header_only_with_key():
    seen = {}
    def h(req):
        seen["auth"] = req.headers.get("authorization")
        return httpx.Response(200, json={"data": [{"id": EP.model}]})
    run(h); assert seen["auth"] is None
    run(h, key="k"); assert seen["auth"] == "Bearer k"

def test_mock_mode_skips_requests():
    s = Settings.from_env({"LLM_MOCK": "1"})
    def fail(req): raise AssertionError("no request expected")
    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(fail)) as c:
            return await run_checks(s, c)
    results = asyncio.run(go())
    assert [r.name for r in results] == ["Fast model", "Smart model"]
    assert all(r.ok and r.detail == "mock mode" for r in results)
```

- [ ] **Step 2: Run to verify they fail**

Run: `pytest tests/test_health.py -v` — Expected: FAIL, `ModuleNotFoundError`.

- [ ] **Step 3: Implement `check_model` and `run_checks` in `baseapp/health.py`** (`asyncio.gather` for concurrency; `time.perf_counter` for `ms`)

- [ ] **Step 4: Run to verify they pass**

Run: `pytest tests/test_health.py -v` — Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: model endpoint health checks"
```

---

### Task 4: Web app, placeholder page and vendored assets

**Files:**
- Create: `scripts/vendor-assets.sh`, `baseapp/static/**`, `baseapp/templates/base.html`, `baseapp/templates/placeholder.html`, `baseapp/templates/partials/checks.html`, `baseapp/main.py`
- Test: `tests/test_main.py`

**Interfaces:**
- Consumes: `Settings.from_env` (Task 1), `load_app_spec`, `AppSpec`, `AppSpecError` (Task 2), `run_checks`, `CheckResult` (Task 3).
- Produces:
  - `create_app(settings: Settings) -> FastAPI`, and module-level `app = create_app(Settings.from_env())` in `baseapp/main.py`. `app.yaml` is loaded once at startup; on `AppSpecError` the app uses `AppSpec()` and keeps the error text.
  - Routes: `GET /` (placeholder while `spec.screens` is empty; in phase 1 it is always the placeholder); `GET /health`, `GET /healthz` → `{"status": "ok"}`; `GET /api/version` → `{"commit", "platform", "app", "config_error"}`; `GET /api/checks` → JSON list of `CheckResult` dicts, or the `partials/checks.html` fragment when the request has the `HX-Request` header. The first row is always `App` (ok, `"running <commit[:7]>"`).
  - `base.html` blocks `title` and `content`; header shows the mark (icon or letter on the brand color), the app name, and the `Air-gap capable` badge; the footer line reads `Data stays in <spec.site or settings.site_name>`.

- [ ] **Step 1: Vendor the assets**

`scripts/vendor-assets.sh` downloads npm tarballs with `curl` from `https://registry.npmjs.org/` (pinned versions recorded in the script) and copies out: `htmx.org` → `vendor/htmx.min.js`; `@fontsource/atkinson-hyperlegible-next` and `@fontsource/atkinson-hyperlegible-mono` → latin 400 and 700 `.woff2`; `lucide-static` → `shield.svg`, `circle-check.svg`, `triangle-alert.svg`, `wifi-off.svg`, `server.svg`. Run it once and commit the outputs. The script runs only on a developer machine, never during an image build.

- [ ] **Step 2: Write the failing tests**

```python
import html as htmllib, re
from fastapi.testclient import TestClient
from baseapp.config import Settings
from baseapp.main import create_app

def client(tmp_path, yaml_text=None, **env):
    if yaml_text is not None:
        (tmp_path / "app.yaml").write_text(yaml_text)
    return TestClient(create_app(Settings.from_env({"APP_DIR": str(tmp_path), "LLM_MOCK": "1", **env})))

def test_health_both_paths(tmp_path):
    c = client(tmp_path)
    assert c.get("/health").json() == {"status": "ok"}
    assert c.get("/healthz").json() == {"status": "ok"}

def test_docs_off_openapi_on(tmp_path):
    c = client(tmp_path)
    assert c.get("/docs").status_code == 404
    assert c.get("/openapi.json").status_code == 200

def test_placeholder_shows_brand_badge_and_site(tmp_path):
    html = client(tmp_path, 'name: Alert Triage\nbrand: "#1D4ED8"\nsite: HQ data center\n').get("/").text
    assert "Alert Triage" in html and "#1D4ED8" in html
    assert "Air-gap capable" in html and "Data stays in HQ data center" in html

def test_bad_config_still_serves_and_reports(tmp_path):
    c = client(tmp_path, "brand: blue\n", APP_COMMIT="abc1234def")
    assert c.get("/health").status_code == 200
    assert 'brand "blue" is not valid' in htmllib.unescape(c.get("/").text)
    v = c.get("/api/version").json()
    assert v["commit"] == "abc1234def" and v["config_error"].startswith("app/app.yaml:")

def test_checks_json_and_fragment(tmp_path):
    c = client(tmp_path, APP_COMMIT="abc1234def")
    rows = c.get("/api/checks").json()
    assert [r["name"] for r in rows] == ["App", "Fast model", "Smart model"]
    assert rows[0]["detail"] == "running abc1234"
    frag = c.get("/api/checks", headers={"HX-Request": "true"}).text
    assert "<html" not in frag and "mock mode" in frag

def test_no_external_urls_in_pages_or_css(tmp_path):
    c = client(tmp_path)
    bodies = [c.get("/").text, c.get("/static/css/base.css").text]
    for body in bodies:
        urls = re.findall(r"https?://[^\s\"')]+", body)
        assert [u for u in urls if not u.startswith("http://www.w3.org/")] == []
```

- [ ] **Step 3: Run to verify they fail**

Run: `pytest tests/test_main.py -v` — Expected: FAIL, `ModuleNotFoundError: baseapp.main`.

- [ ] **Step 4: Implement `create_app` and the templates**

The placeholder heading reads `Your app will appear here`, with the line `Ask OpenClaw to build it. This page checks what it needs.` The checks list loads with `hx-get="/api/checks" hx-trigger="load, every 10s"`; each row shows a `circle-check` icon in `#0E7A5F` or a `triangle-alert` icon in `#A85B00`, the name, the detail and the time in ms. `base.css` declares `@font-face` from `/static/vendor/fonts/` and sets the brand through a `--brand` custom property written inline from `spec.brand`. Inline the SVG icons in the templates so the page needs no extra requests. Use one shared `httpx.AsyncClient`, opened and closed in the FastAPI `lifespan`.

- [ ] **Step 5: Run to verify they pass**

Run: `pytest -v` — Expected: all tests pass (Tasks 1–4).

- [ ] **Step 6: Look at it**

Run: `APP_DIR=team-repo/app LLM_MOCK=1 uvicorn baseapp.main:app --port 8742` (after Task 6 creates `team-repo/app`, or point `APP_DIR` at a temp folder now) and open `http://localhost:8742/`. Expected: brand header, badge, three passing checks marked "mock mode", no failed requests in the browser network tab.

- [ ] **Step 7: Commit**

```bash
git add -A && git commit -m "feat: placeholder page with live health checks and vendored assets"
```

---

### Task 5: Base image

**Files:**
- Create: `baseapp/__main__.py`, `Containerfile`, `.dockerignore`, `scripts/verify-image.sh`

**Interfaces:**
- Consumes: `baseapp.main:app` (Task 4), `Settings.from_env` for `port`.
- Produces: image `base-app` with the virtualenv at `/opt/venv`, the package at `/opt/base-app/baseapp`, `PYTHONPATH=/opt/base-app`, `APP_DIR=/opt/app-root/app`, `APP_PORT=8742`, `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUNBUFFERED=1`, `USER 1001`, `CMD ["python", "-m", "baseapp"]`. Task 6's team `Dockerfile` relies on these paths.

- [ ] **Step 1: Write `scripts/verify-image.sh IMAGE`**

It runs `podman run -d --read-only --tmpfs /tmp --user 1000770000:0 -p 18742:8742 -e LLM_MOCK=1 IMAGE`, polls `http://127.0.0.1:18742/healthz` every 50 ms, and prints `ready in <ms> ms`. It fails if ready takes 1000 ms or more. After 5 s idle, it reads memory from `podman stats --no-stream --format '{{.MemUsage}}'`, prints `idle memory <MiB> MiB`, and fails at 64 MiB or more. It always removes the container.

- [ ] **Step 2: Run it against a missing image to verify it fails**

Run: `scripts/verify-image.sh localhost/base-app:dev` — Expected: non-zero exit, image not found.

- [ ] **Step 3: Write `baseapp/__main__.py` and the `Containerfile`**

Builder stage: `python3.12 -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt`. Runtime stage: copy `/opt/venv` and `baseapp/`; run `python -m compileall -q /opt/venv /opt/base-app` so no bytecode is written at runtime; `chgrp -R 0` and `chmod -R g=u` on `/opt/venv`, `/opt/base-app` and `/opt/app-root`. `__main__.py` calls `uvicorn.run("baseapp.main:app", host="0.0.0.0", port=settings.port, workers=1, access_log=False)`.

- [ ] **Step 4: Build and verify**

```bash
podman build -t localhost/base-app:dev -f Containerfile .
podman run --rm localhost/base-app:dev python -c "import fastapi, baseapp; print('ok')"
scripts/verify-image.sh localhost/base-app:dev
```

Expected: `ok`, then `ready in <1000 ms` and `idle memory <64 MiB`, exit 0. If the venv's interpreter path differs between the builder and the minimal image, the import check fails first; point the venv at `/usr/bin/python3.12`, which both images ship.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: base image on ubi9 python-312-minimal"
```

---

### Task 6: Team repo template

**Files:**
- Create: `team-repo/Dockerfile`, `team-repo/Makefile`, `team-repo/team.env.example`, `team-repo/.gitignore`, `team-repo/app/app.yaml`, `team-repo/.gitea/workflows/build-deploy-openshift.yml`, `baseapp/wait.py`, `scripts/build-team-repo.sh`
- Test: `tests/test_wait.py`

**Interfaces:**
- Consumes: the base image paths from Task 5.
- Produces:
  - `team-repo/Dockerfile`: `ARG BASE_IMAGE=base-app:latest`, `FROM ${BASE_IMAGE}`, `ARG APP_COMMIT=dev`, `ENV APP_COMMIT=${APP_COMMIT}`, `COPY app/ /opt/app-root/app/`.
  - `baseapp.wait.wait_for_commit(url: str, commit: str, timeout: float = 300, interval: float = 2, insecure: bool = True, fetch: Callable[[str], dict] | None = None) -> float`. It polls `{url}/api/version` until `commit` matches, returns the seconds elapsed, and raises `TimeoutError("<url> still reports <seen> after 300 s; expected <commit>")`. `python -m baseapp.wait` reads `APP_URL` from the environment and the commit from `git rev-parse HEAD`, then prints `live in <s> s at <url>`. It uses only the standard library (`urllib`, `ssl`).
  - `dist/team-repo/`, produced by `scripts/build-team-repo.sh`: the contents of `team-repo/`, plus `platform/baseapp/` and `platform/requirements.txt`.
  - `make dev`: creates `.venv` from `platform/requirements.txt` if it is missing, loads `team.env`, then runs `uvicorn baseapp.main:app --reload --reload-dir app --port 8742` with `PYTHONPATH=platform APP_DIR=app`. `make wait`: loads `team.env` and runs `python -m baseapp.wait`.
  - `team.env.example` keys: `TEAM`, `GITEA_REMOTE`, `APP_URL`, the seven `LLM_*`/`SITE_NAME` variables as the user VM reaches the models.

- [ ] **Step 1: Write the failing tests**

```python
import pytest
from baseapp.wait import wait_for_commit

def test_returns_when_commit_matches():
    seen = iter([{"commit": "old"}, {"commit": "new"}])
    assert wait_for_commit("http://a", "new", interval=0, fetch=lambda u: next(seen)) >= 0

def test_tolerates_unreachable_while_rolling_out():
    calls = iter([OSError("refused"), {"commit": "new"}])
    def fetch(u):
        r = next(calls)
        if isinstance(r, Exception): raise r
        return r
    wait_for_commit("http://a", "new", interval=0, fetch=fetch)

def test_times_out_with_what_it_saw():
    with pytest.raises(TimeoutError, match="still reports old after"):
        wait_for_commit("http://a", "new", timeout=0.01, interval=0, fetch=lambda u: {"commit": "old"})
```

- [ ] **Step 2: Run to verify they fail**

Run: `pytest tests/test_wait.py -v` — Expected: FAIL, `ModuleNotFoundError`.

- [ ] **Step 3: Implement `baseapp/wait.py`, then write the template files**

The workflow is `openclaw-demo/team-app/.gitea/workflows/build-deploy-openshift.yml` with one change: the `Start OpenShift build` step passes `GITEA_SHA: ${{ gitea.sha }}` in `env` and adds `--build-arg APP_COMMIT="${GITEA_SHA}"` to `oc start-build`. `team-repo/app/app.yaml` holds `name: Team app` and `screens: []`, with comments naming each field. `.gitignore` lists `.venv/`, `team.env`, `memory/`, `MEMORY.md`.

- [ ] **Step 4: Run to verify they pass**

Run: `pytest -v` — Expected: all pass.

- [ ] **Step 5: Build a team image from the template and check the commit flows through**

```bash
scripts/build-team-repo.sh
cd dist/team-repo
podman build -t localhost/team-test:dev --build-arg BASE_IMAGE=localhost/base-app:dev --build-arg APP_COMMIT=0123456789abcdef .
podman run -d --name tt -p 18742:8742 -e LLM_MOCK=1 localhost/team-test:dev
sleep 1 && curl -s localhost:18742/api/version; podman rm -f tt
```

Expected: `"commit":"0123456789abcdef"` and `"app":"Team app"`.

- [ ] **Step 6: Check `make dev` from the assembled template**

Run in `dist/team-repo`: `cp team.env.example team.env`, set `LLM_MOCK=1`, run `make dev`, open `http://localhost:8742/`, edit `app/app.yaml` `name:`, and reload the page. Expected: the new name appears after the reload. Stop with Ctrl-C.

- [ ] **Step 7: Commit**

```bash
git add -A && git commit -m "feat: team repo template with make dev and make wait"
```

---

### Task 7: Wire into `openshift-automation` and `start-lab.sh`

**Files (all under `openclaw-demo/`):**
- Create: `openshift-automation/templates/base-app-imagestream.yaml`, `openshift-automation/templates/base-app-buildconfig.yaml`
- Modify: `openshift-automation/templates/buildconfig.yaml`, `openshift-automation/templates/deployment.yaml`, `openshift-automation/team.env.example`, `openshift-automation/scripts/render-openshift-manifests.sh`, `openshift-automation/scripts/bootstrap-openshift-cicd.sh`, `start-lab.sh`

**Interfaces:**
- Consumes: `base-app/Containerfile` (Task 5), `base-app/scripts/build-team-repo.sh` and `dist/team-repo/` (Task 6).
- Produces: in each team namespace, ImageStream `base-app`, BuildConfig `base-app` (binary source, Docker strategy, `dockerfilePath: Containerfile`, output `base-app:latest`), and a team BuildConfig whose `dockerStrategy.from` is `{kind: ImageStreamTag, name: "base-app:latest"}`.

- [ ] **Step 1: Write the expected render as a check**

Create `openshift-automation/scripts/check-render.sh`. It sources `team.env.example`, runs `render-openshift-manifests.sh`, and greps the output. It fails unless the output contains `containerPort: 8742`, `path: /healthz`, `memory: 64Mi`, `memory: 256Mi`, `cpu: 25m`, `readOnlyRootFilesystem: true`, `mountPath: /tmp`, `name: LLM_FAST_URL`, `name: LLM_SMART_MODEL`, `name: base-app:latest`. It also fails if the output contains `persistentVolumeClaim`, `SIMULATOR_ENABLED` or `LLM_BASE_URL`.

- [ ] **Step 2: Run it to verify it fails**

Run: `openshift-automation/scripts/check-render.sh` — Expected: FAIL on the first missing string. (`envsubst` comes from `brew install gettext` if it is missing.)

- [ ] **Step 3: Change the templates and scripts**

- `deployment.yaml`: remove the `data` PVC volume and mount and the `DB_PATH`, `SIMULATOR_*` and `LLM_BASE_URL`/`LLM_MODEL`/`LLM_TIMEOUT_SECONDS` env vars. Add an `emptyDir` named `tmp` at `/tmp` and set `readOnlyRootFilesystem: true`. Add the seven env vars from `${LLM_FAST_URL}` and the others; `LLM_API_KEY` stays a `secretKeyRef` with `optional: true`. Set resources to the Global Constraints values. Both probes use `/healthz` on `http`, readiness `initialDelaySeconds: 1, periodSeconds: 5`. Keep port 8742.
- `buildconfig.yaml`: add `from: {kind: ImageStreamTag, name: "base-app:latest"}` under `dockerStrategy`.
- `team.env.example`: drop `STORAGE_CLASS` and `DATA_PVC_SIZE`. Add `LLM_FAST_URL`, `LLM_FAST_MODEL`, `LLM_SMART_URL`, `LLM_SMART_MODEL`, `LLM_MOCK=0`, `SITE_NAME="dCloud lab"`, using the in-cluster URLs; the fast URL is a placeholder until the user supplies it.
- `render-openshift-manifests.sh` and `bootstrap-openshift-cicd.sh`: export the six new variables, with the same defaults, alongside the existing exports.
- `bootstrap-openshift-cicd.sh`: delete the PVC block. After `apply_template buildconfig`, apply `base-app-imagestream` and `base-app-buildconfig`, then copy only `Containerfile`, `requirements.txt` and `baseapp/` from `${BASE_APP_DIR}` into a `mktemp -d` folder (so `.venv/`, `.git/` and `dist/` are never uploaded) and run `oc start-build base-app --from-dir="<that folder>" --follow --wait -n "${OPENSHIFT_NAMESPACE}"`. `BASE_APP_DIR` defaults to `${ROOT}/../../base-app`; the script dies with a clear message if `${BASE_APP_DIR}/Containerfile` is missing.
- `start-lab.sh`: default `TEAM_APP_DIR` to `${SCRIPT_DIR}/../base-app/dist/team-repo`. Before seeding, run `${SCRIPT_DIR}/../base-app/scripts/build-team-repo.sh` so the template matches the source. Change the Contents API commit message to `Add base-app placeholder and OpenShift workflow`.

- [ ] **Step 4: Run the render check to verify it passes**

Run: `openshift-automation/scripts/check-render.sh` — Expected: `render OK`, exit 0. Also run `bash -n` on each modified script.

- [ ] **Step 5: Commit**

`openclaw-demo/` is not a git repo today. Commit inside `base-app/` only, and report the changed `openclaw-demo` files in the hand-off so the user can carry them into whatever tracks the lab automation.

---

### Task 8: Cluster acceptance (run by the user; no `oc` on this machine)

**Files:**
- Create: `base-app/docs/acceptance-phase-1.md`, which records the numbers below.

- [ ] **Step 1: Fresh namespace**

Run `start-lab.sh` for one unused team as usual. Expected: bootstrap prints the `base-app` build finishing, the team build succeeds, and the Route shows the placeholder with `App`, `Fast model` and `Smart model` all passing.

- [ ] **Step 2: Footprint**

Run `oc adm top pod -l app=<team> -n <ns>` after 1 minute idle, and read the readiness time from `oc get events` (container started → readiness passed). Expected: under 64 MiB, and ready in under 1 s.

- [ ] **Step 3: One-line change**

Clone the team repo on the user VM, change `name:` in `app/app.yaml`, then commit, push and run `make wait`. Expected: `live in <60 s>`, and the new name on the page.

- [ ] **Step 4: Record**

Write the three measured numbers and the date into `docs/acceptance-phase-1.md`, and commit.
