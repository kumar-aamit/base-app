# base-app: decisions and file tree

Where the base-app platform and each lab user's repo stand as of 2026-11-26 (branch `final`, created
from tag `phase-2`). The design paper is `base-app-paper.md`; where this file and the paper differ,
this file describes what is built.

## v2 (branch `v2`)

What changed from v1 on `main`, from the design review on 2026-11-26. Where this section and the
rest of this file differ, this section wins.

| Area | v2 |
|---|---|
| Default app | **Mock App** opens on a **System status** page instead of the start page. Ten tiles: App, Fast model, Smart model, Knowledge, Air-gapped, Private data, Token cost, Data residency, Under load, Model version. Each has an (i) with its meaning on hover or focus. |
| Live demos | *Ask the fast model* (classify a log line), *Ask the smart model* (why a hospital runs AI on-site) and *10 requests at once* to the fast model. Each shows time, tokens and $0. Mock mode says no model was called and shows no made-up timings. |
| Prompts | Not in the app. Each guided use case has a brief in `catalog/` with its prompts; the lab guide's appendix shows the same prompts. `start.py`, `usecases.yaml`, the start page and its script are removed. |
| Header | No Air-gap capable badge. A **System status** link with a live dot appears once the app has a screen; screen tabs move into the header. |
| Status chips | A row above each screen: `airgap`, `stored`, `runs`, `last`, `model`, `knowledge`, chosen and renamed with `status:` in the screen file, updated after every run. |
| Version | Footer: `<app> v<N> · build <commit> · deployed <time> · base-app <version>`. N is `APP_VERSION`, else the trailing number of `OPENSHIFT_BUILD_NAME`, which OpenShift sets in Docker-strategy builds (to confirm on the cluster). Platform version 0.2.0. |
| Tokens | The model client reads `usage.total_tokens` (or estimates 4 characters a token) and strips `<think>` blocks. Counters live in memory and reset with each build. |
| Precision | `LLM_FAST_PRECISION` (default FP8) and `LLM_SMART_PRECISION` (default NVFP4) label the models on tiles and chips. Set them to how each model is served. |
| Answers | `score` takes `higher: worse` or `higher: better` for red, amber and green bands. Table columns named Severity, Risk or Priority show colored chips; Line, Fix, Command and Config line are monospace. |
| Lead network example | `examples/netconf-guard/app/`: NetConf Guard, screen Network Config Review, three sample configs, a 25-rule hardening standard. Brief: `catalog/netconf-guard.md`. |
| Icons | Nine more Lucide icons vendored: zap, cpu, search, lock, coins, landmark, gauge, sliders-horizontal, info. |

Still as v1: review layout only, no streaming or chat, stateless pods, port 8742, `make check`,
`make wait`, `make smoke`. GUIDE.md still walks through Alert Triage and points to NetConf Guard
as the alternative; `base-app-paper.md` and the walkthrough under `docs/walkthrough/` describe v1.

## Decisions

### Locked

These are settled; reopen them only with the lab owner.

| Decision | Detail |
|---|---|
| Lead app | Alert Triage in the review layout, built in three prompts: Build, Ground it, Shape the answer. Event desk stays in the catalog only. |
| Kit scope | The review layout only. Workspace, assistant, streaming and chat stay in phase 3. |
| Generic terms in user-facing copy | Agentic harness (then "the harness"), code repo, Kubernetes cluster, k8s namespace, open-weights model (fast tier / smart tier), OpenAI-compatible API, app URL. Cisco AI Pod and dCloud keep their names. File names, env vars, model IDs, scripts, Make targets and workflow internals keep theirs. |

### Lab shape

| Decision | Detail |
|---|---|
| One platform, one folder per user | Every lab user's repo is the platform plus one `app/` folder. The agentic harness edits only `app/`. |
| Lead use case | Alert Triage (IT security), built in the Review layout in three prompts: Build, Ground it, Shape the answer. |
| Repo name | One repo per lab user, `user-<N>` from the lab user number (`user7` → `user-7`). The lab is single-user sessions: each user has their own repo, k8s namespace, app URL and harness. `start-lab.sh` derives the name today as `team-<N>`; rename it there. |
| Base image build | dCloud automation builds and deploys the base image at lab start. Lab users never build it. |
| App image | The repo's `Dockerfile` is `FROM ${BASE_IMAGE}` plus `COPY app/` and an `APP_COMMIT` build arg. |
| Seeding | `scripts/build-lab-repo.sh` writes `dist/lab-repo/`; `start-lab.sh` commits it into each user's code repo through the repo server's Contents API (`LAB_APP_DIR`). The `start-lab.sh` wiring is still to do. |

### Repo layout

| Decision | Detail |
|---|---|
| The repo root is laid out as a lab user's repo | What you open is what each lab user gets, plus base-app tooling beside it. |
| `platform/baseapp/` is the source | Not a generated copy. The package is `baseapp`, not `platform`, which would shadow the standard library. |
| Seed by explicit list | `SEED` in `build-lab-repo.sh`: GUIDE.md, guide-images, AGENTS.md, Dockerfile, Makefile, lab.env.example, .gitignore, .gitea, app, catalog, examples, skills, platform. |
| Base-app only | Containerfile, .dockerignore, tests, scripts, docs, base-app-paper.md, pyproject.toml, requirements-test.txt. `tests/test_seed.py` fails if a new top-level path is in neither list. |
| `platform/PIN` | A hash of `platform/baseapp`, written only into the seeded copy. `make check` in a lab user's repo fails if `platform/` was edited; in this repo it skips the comparison. |
| Working copy | `/Users/amitkumar/PycharmProjects/hackathon-v2`. The older copy under `Documents/demo-guide/base-app` is stale. Remote `origin` is the public GitHub repo `kumar-aamit/base-app` (`main`, tags `phase-1` and `phase-2`); `final` is pushed too. |

### Stack and runtime

| Decision | Detail |
|---|---|
| Stack | Python 3.12, FastAPI, Jinja2 templates, htmx. No frontend build. |
| Dependencies | Seven pins: fastapi 0.165.0, uvicorn 0.54.0, jinja2 3.1.6, httpx 0.28.1, pyyaml 6.0.4, python-multipart 0.0.34, pypdf 7.1.1. Dev only: watchfiles 1.3.0, pytest 9.2.0. |
| Nothing from the internet | htmx 2.0.11, Atkinson Hyperlegible Next and Mono 5.3.0 and lucide-static 1.79.0 icons are vendored. FastAPI's `/docs` and `/redoc` are off. `make check` rejects external URLs in `app/`. |
| Port and health | Port 8742. `/health` and `/healthz` both answer `{"status": "ok"}`. `/api/version` reports the running commit for `make wait`. |
| Base image | Two stages, ubi9 python-312 into python-312-minimal; runs as any UID in group 0 with a read-only root and `/tmp` as emptyDir. Measured: ready in 247 ms, idle at 35.4 MiB. |
| Pod sizing (planned) | Requests 25m CPU / 64Mi, limits 500m / 256Mi, set in the Deployment template with Task 7. |
| Stateless | No database. Knowledge is indexed in memory at startup. |
| Start page | `/` shows it until `app.yaml` lists a screen; `/start` always does, linked from every footer. Ten use cases from `platform/baseapp/usecases.yaml` (in the base image, since `catalog/` is not in the app image); Alert Triage's three prompts must match its brief word for word. Steps tick from what the app has: a screen, then `knowledge:` and a checklist, then a score and a table. It polls `/api/version` and reloads on a new build. No harness progress and no model call: the app cannot see the harness. |
| Lab user label | `LAB_USER` in the Deployment's environment shows `· user-7` beside the app name; unset, nothing shows. |

### Models

| Decision | Detail |
|---|---|
| Two tiers, both run | Open-weights models behind an OpenAI-compatible API. fast tier: an 8B instruct model. smart tier: a 120B mixture of experts, default ID `nvidia/nemotron-3.5-super`. Set with `LLM_FAST_URL`, `LLM_FAST_MODEL`, `LLM_SMART_URL`, `LLM_SMART_MODEL`, `LLM_API_KEY`. The fast URL is not supplied yet. |
| Client | Plain httpx to the OpenAI-compatible `/chat/completions`; no SDK. Temperature 0.2, max 4096 tokens, 120 s timeout. |
| Structured answers | Each screen's answer blocks become a JSON schema sent as `response_format`; the reply is checked against it. |
| Reasoning switch | `reasoning: off` sends `chat_template_kwargs: {enable_thinking: false}`. |
| Mock mode | `LLM_MOCK=1`: no model is called; each example's `mock:` answer is returned, or a placeholder built from the blocks. The placeholder page shows model checks as grey "skipped: mock mode", not green. |

### What a user writes in app/

| Decision | Detail |
|---|---|
| Fixed files | `app.yaml`; `screens/<name>.yaml` and `prompts/<name>.md` for every name in `screens:`. |
| Optional | `knowledge/` (any folder inside `app/` a screen names; absolute paths, `..` and symlinks to anything outside `app/` are rejected), `data/` (convention; required only by `ctx.data` and `ctx.text`), `hooks.py`. |
| app.yaml fields | `name` (1 to 40 characters), `mark` (one letter or a vendored icon), `brand` (hex, at least 4.5:1 against white), `site`, `screens`. |
| Layouts | Only `review` in this platform version. `workspace` and `assistant` are rejected with a message saying so (phase 3). |
| Inputs | text, textarea, select (a list or the first column of a CSV), number, toggle, file (.txt .log .csv .md .json .pdf become text, up to 2 MB). |
| Answer blocks | text, score `{value 0-100, label}`, table (with `columns:`), checklist `{step, source}`. Charts, streaming and chat are phase 3. |
| Examples | Each is a chip in the UI and a test in `make check`. Every screen needs at least one. |
| Prompts | Jinja2 with undefined names as errors. They get every input, every hook value, `site` and `app_name`. |
| Knowledge search | BM25 in pure Python. Markdown splits at headings, and each section is also found by its document's title. The 4 best passages are appended as `[n] file — heading`; checklist sources cite them. |
| Hooks | `prepare(ctx)` returns a dict of new prompt values. Standard library only; `ctx.data()` and `ctx.text()` read only from `app/data/`. |
| Error messages | Name the file, the field and the fix, so a model can act on them. |

### Commands

| Command | What it does |
|---|---|
| `make dev` | Runs the app on port 8742 with live reload of `app/`. |
| `make check` | Under 5 s, no GPU: platform PIN; external URLs; stdlib-only hook imports; app.yaml and every screen, with `knowledge:` confined to `app/`; brand contrast; every screen renders; every example runs end to end against the mock and renders; mock citations exist. |
| `make wait` | Waits until the user's app URL serves the pushed commit. |
| `make smoke` | Runs every example against the deployed app and real models and prints timings. |

### Trust signals

| Signal | Where |
|---|---|
| Air-gap capable badge | Header of every page. |
| Privacy note | Under the inputs: "What you enter stays in {site}. It goes only to the {tier} model server on-site." |
| Response route | Under every answer: device to app to model, with the browser-measured total and the model time; "Mock answer: no model was called" in mock mode. |
| Footer | "Data stays in {site}", the platform version and the build commit. |

## Open items

- On-cluster acceptance run (phase 1 Task 8). Still to rename in the automation: `team-<N>` to `user-<N>` and `team.env` to `lab.env`. Found on the first manual run (`team-1`): the `project-resources` quota rejects build pods without `resources.limits`, and a BuildConfig without `dockerStrategy.from` looks up the `Dockerfile`'s `FROM base-app:latest` on public registries and fails.
- Done in openclaw-demo `a656f65` (phase 1 Task 7, changed from per-namespace to shared): bootstrap builds `base-app:latest` once per lab in `BASE_APP_NAMESPACE` (default `base-app`) with limits set, only when the tag is missing or `BASE_APP_REBUILD=1`, and grants each user namespace `system:image-puller`. Each user's BuildConfig sets `dockerStrategy.from` to that tag. The Deployment drops the PVC and old app env, sets the `LLM_*` tiers, `LAB_USER` and `SITE_NAME`, and probes `/healthz`. `start-lab.sh` seeds from `build-lab-repo.sh` (`LAB_APP_DIR`, `TEAM_APP_DIR` still accepted).
- Decide whether the lab-start machine fetches the public GitHub repo or a copy on the lab's code repo server.
- Run the examples against the real models; every screenshot so far is mock mode.
- Phase 3: workspace and assistant layouts, streaming, follow-up chat, charts, image input. Phase 4: the other 26 catalog briefs and harness provisioning.
- A whole-branch code review has not been done.

Done on `final`:

- [x] Confine `knowledge:` to folders inside `app/`: absolute paths, `..` and symlinks out of `app/` fail at load time and in `make check`.
- [x] Add to the skill: quote YAML values that contain `, ? : #`. (`AGENTS.md` has no YAML section, so the rule is only in the skill.)
- [x] Update the paper: the repo's `Dockerfile`, review layout only, Alert Triage in three prompts, generic terms, and unbuilt features marked phase 3 or phase 4.
- [x] Create a git remote: `origin` on GitHub.
- [x] Single-user lab sessions: no "team" for the lab user anywhere. `lab.env` (`LAB_USER`), `build-lab-repo.sh`, `dist/lab-repo/`, repos named `user-<N>`, and the default app name "Your app".
- [x] Start page replaces the placeholder: ten use cases, copy buttons, live step ticks, reload on a new build, `/start` from every footer, `LAB_USER` label. Bundled fonts only.

## File tree

Tracked files on `final`. Vendored assets, plans and screenshots are collapsed (`…`), and so are the
gallery apps and walkthrough steps, which have the same shape as `examples/alert-triage/app/`.
Paths marked **seeded** are what `build-lab-repo.sh` copies into every lab user's repo.

```text
hackathon-v2/
├── .gitea/workflows/build-deploy-openshift.yml   seeded: build and deploy on push
├── app/                                          seeded: THE user's app; starts empty (the start page)
│   └── app.yaml
├── catalog/                                      seeded: briefs a first prompt can name
│   └── it-alert-triage.md
├── docs/                                         base-app only
│   ├── decisions.md                              this file
│   ├── gallery/                                  one app per industry, mock screenshots
│   │   ├── alarm-flood/app/…
│   │   ├── aml-narrator/app/…
│   │   ├── clause-review/app/…
│   │   ├── config-auditor/app/…
│   │   ├── discharge/app/…
│   │   ├── line-assist/app/…
│   │   ├── records-release/app/…
│   │   ├── shrink-analyst/app/…
│   │   ├── *.png
│   │   └── README.md
│   ├── screenshots/…                             phase 1 placeholder screenshots
│   │   └── final/                                alert-triage-final.png, start-page*.png
│   ├── superpowers/…                             roadmap and phase plans
│   └── walkthrough/alert-triage/                 app/ after each of the three prompts
│       ├── step-1-build/app/…
│       ├── step-2-ground/app/…
│       ├── *.png
│       ├── app-yaml.md
│       └── README.md
├── examples/                                     seeded: finished apps to copy patterns from
│   └── alert-triage/app/                         = step 3 of the walkthrough
│       ├── data/
│       │   ├── assets.csv
│       │   ├── vpn-lockout.log
│       │   └── vpn-spray.log
│       ├── knowledge/
│       │   ├── malware-beacon.md
│       │   ├── password-spray.md
│       │   └── phishing.md
│       ├── prompts/
│       │   └── triage.md
│       ├── screens/
│       │   └── triage.yaml
│       ├── app.yaml
│       └── hooks.py
├── platform/                                     seeded (+ PIN); read-only for users
│   ├── baseapp/                                  the platform source
│   │   ├── static/
│   │   │   ├── css/base.css
│   │   │   ├── js/review.js, js/start.js
│   │   │   └── vendor/…                          htmx, fonts, icons
│   │   ├── templates/
│   │   │   ├── layouts/review.html
│   │   │   ├── partials/
│   │   │   │   ├── answer.html
│   │   │   │   ├── checks.html
│   │   │   │   ├── input.html
│   │   │   │   ├── run_error.html
│   │   │   │   └── status.html                   the start page's check strip
│   │   │   ├── base.html
│   │   │   └── start.html
│   │   ├── __init__.py
│   │   ├── __main__.py                           python -m baseapp: uvicorn on APP_PORT
│   │   ├── appspec.py                            app.yaml
│   │   ├── blocks.py                             answer blocks: schema, placeholder, checks
│   │   ├── check.py                              make check
│   │   ├── config.py                             settings from the environment
│   │   ├── files.py                              uploads to text
│   │   ├── health.py                             model endpoint checks
│   │   ├── hookrunner.py                         hooks.py and ctx
│   │   ├── knowledge.py                          BM25 search
│   │   ├── llm.py                                model client
│   │   ├── main.py                               routes
│   │   ├── pin.py                                platform/PIN hash
│   │   ├── runner.py                             one run: inputs → hooks → search → prompt → model
│   │   ├── screens.py                            screen files
│   │   ├── smoke.py                              make smoke
│   │   ├── start.py                              start page: use cases, steps done, preview
│   │   ├── usecases.yaml                         the ten use cases and their prompts
│   │   └── wait.py                               make wait
│   ├── requirements-dev.txt
│   └── requirements.txt
├── scripts/                                      base-app only
│   ├── build-lab-repo.sh                         writes dist/lab-repo/
│   ├── vendor-assets.sh                          refreshes platform/baseapp/static/vendor/
│   └── verify-image.sh                           restricted-pod run: ready < 1 s, idle < 64 MiB
├── skills/                                       seeded: the harness skill
│   └── base-app/SKILL.md
├── tests/                                        base-app only; 109 tests
│   ├── test_appspec.py
│   ├── test_check_smoke.py
│   ├── test_config.py
│   ├── test_health.py
│   ├── test_knowledge_files_hooks.py
│   ├── test_llm_runner.py
│   ├── test_main.py
│   ├── test_review_web.py
│   ├── test_screens.py
│   ├── test_seed.py
│   ├── test_start.py
│   ├── test_wait.py
│   └── test_walkthrough.py
├── .dockerignore                                 base-app only
├── .gitignore                                    seeded
├── AGENTS.md                                     seeded: the 9 rules the harness follows
├── GUIDE.md                                      seeded: the lab user's step-by-step guide
├── guide-images/                                 seeded: the step screenshots GUIDE.md shows
├── base-app-paper.md                             base-app only: the design paper
├── Containerfile                                 base-app only: the base image
├── Dockerfile                                    seeded: the app image
├── Makefile                                      seeded: dev, check, wait, smoke
├── pyproject.toml                                base-app only: pytest settings
├── requirements-test.txt                         base-app only
└── lab.env.example                               seeded
```
