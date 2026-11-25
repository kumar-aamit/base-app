# base-app: Sovereign AI Platform & Use Case Catalog

## Summary

Build one small Python platform, base-app, that every team's app runs on. Each team's Gitea repo holds the platform plus one `app/` folder, and OpenClaw builds the team's app in that folder from a few short prompts. End users see only the finished app, under its own name and brand.

- **Stack:** Python 3.12, FastAPI, Jinja2 and htmx on Red Hat's minimal Python image. There is no frontend build, and every font, script and stylesheet ships in the image, so the app never calls outside the cluster.
- **One app per repo:** `app/app.yaml` sets the app's name, mark, brand color and screens. Each screen uses one of three layouts filled with platform components, so most apps need no Python.
- **Prompts:** two or three prompts build a working prototype, and each later prompt adds one building block. Teams start from a catalog brief or their own idea.
- **Trust signals:** every app carries an Air-gap capable badge, says where its data stays and times each answer from device to model server.
- **Models:** app pods hold no weights. They call the fast and smart endpoints already running in dCloud, and OpenClaw writes code with the smart one, Nemotron 3.5 Super.
- **Builds:** each push builds FROM base-app plus the `app/` folder in seconds. Pods request 64 MiB and start in about half a second.

Before a team's first prompt, its app shows a plain placeholder with live health checks. Every example in this paper builds one lead app, Alert Triage, chosen below. The catalog lists 27 ideas across 8 industries, the lead among them, each with its reason to run locally.

## Lead use case: Alert Triage

Alert Triage leads because it shows every reason to run AI on-site at once, and every customer has a security team, whatever their industry. An analyst pastes an alert and attaches its logs, and the app returns a verdict, a severity, the attack techniques and next steps from the team's own runbooks.

| Reason to run on-site | What it means for alert triage |
|---|---|
| Free tokens | Teams average 960 alerts a day and leave 40% uninvestigated (survey of 282 security leaders). On owned GPUs, reading every alert with its full logs adds no per-token bill. |
| Sensitive data and IP | Alerts and logs map the network, its users and its unpatched weak spots: exactly what an attacker wants. |
| Regulation | Logs carry personal data, such as usernames and email addresses, that privacy and sector rules restrict. |
| Speed under load | An attack floods the queue just when answers matter most; a local model has no per-minute API quota and no internet round trip. |
| Works offline | Incident response starts by isolating affected systems (CISA), and an outage can take the internet link down too; the on-site model keeps answering. |
| Model control | The model version is pinned, so a verdict can be reproduced in an audit or an after-action review, and prompts stay in the team's own logs. |

It beat three other candidates:

| Candidate | Where on-site wins | Who it reaches |
|---|---|---|
| Alert Triage (chosen) | All six reasons above | Every organization with a security team |
| Maintenance copilot | Latency, offline plant floors, process IP | Manufacturers |
| Clinical documentation | Patient-data rules, validated models | Hospitals and clinics |
| Network config review | Device secrets, model control | Every network team, but as batch work where speed and offline matter less |

The worked example is a password spray: 212 failed VPN logins for 9 users from one address, then a success at 02:14. The same screen serves the network operations center, where an outage alert and its syslog go through the same triage.

## Architecture

Three tiers keep the app small: thin app pods on CPU, a shared GPU model tier, and a build loop that OpenClaw drives.

> [Diagram: architecture — embed node/51bb9589-838d in the original doc]

Users reach their team's app through its own Route. Each pod runs the same base image and calls only the model endpoints. OpenClaw, on each user's VM, writes code with the smart-tier model and pushes to its team's Gitea repo, and the workflow builds and rolls out the new image.

## The stack

base-app runs Python 3.12 with FastAPI, Jinja2 templates and htmx, and streams answers with server-sent events. It is the most common web stack in model training data and has no compile or frontend build step, so OpenClaw extends it reliably and most changes are YAML and Markdown. Pods idle at about 40 MB and are ready in about half a second.

Decisions inside the stack:

- **No frontend build.** Pages render on the server from the app's screen files. htmx swaps page fragments and Server-Sent Events stream model tokens. One hand-written CSS file holds the shared parts; an app's brand changes only its name, mark and color.
- **Nothing loads from the internet.** htmx, a Markdown renderer, an HTML sanitizer, the icon set and the fonts are vendored into the image. FastAPI's default `/docs` page pulls Swagger UI from a public CDN, so it is turned off; `/openapi.json` stays for OpenClaw to read.
- **About seven pinned dependencies:** fastapi, uvicorn, jinja2, httpx, pyyaml, python-multipart for uploads and pypdf for PDF text. No OpenAI SDK, LangChain or vector database: fewer layers for a 120B model to misread, fewer versions to drift.
- **Stateless pods.** No database by default; chat history lives in the browser. Any pod serves any request, so replicas, restarts and scale-to-zero need no extra work.
- **Retrieval without a vector database.** A small pure-Python BM25 keyword index over each app's documents covers lab-sized corpora with no extra service. Embeddings plus pgvector is the upgrade path, added once in the core.

## The app slot: one folder per app

Each team repo has one `app/` folder, and the finished app is whatever that folder describes. OpenClaw writes the folder and the platform turns it into pages, so most apps contain no code and none of them touch the platform.

```text
team-07-app/                the team's Gitea repo
├── AGENTS.md               the rules OpenClaw follows
├── team.env                team number, Gitea remote, app URL
├── Containerfile           FROM base-app, then COPY app/
├── Makefile                dev, check, wait, smoke
├── app/                    the team's app, the only folder OpenClaw edits
│   ├── app.yaml            name, mark, brand color, site, screens
│   ├── screens/            one YAML file per screen
│   ├── prompts/            one Markdown prompt per screen
│   ├── data/               synthetic sample data
│   ├── knowledge/          documents searched before each answer
│   └── hooks.py            optional Python, standard library only
├── catalog/                27 one-page briefs to start from
├── examples/               3 finished apps, one per layout
├── skills/base-app/        the OpenClaw skill: build, add a feature, check
└── platform/               read-only copy for make dev; make check fails if it is edited
```

Alert Triage, the lead example, is two short files plus its prompt and data:

```yaml
# app/app.yaml
name: Alert Triage
mark: shield             # a pictogram from the platform's set, or one letter
brand: "#1D4ED8"         # make check rejects colors that fail contrast with white text
site: HQ data center     # shown in the trust signals
screens: [triage]
```

```yaml
# app/screens/triage.yaml
title: Triage an alert
layout: review           # workspace | review | assistant
model: smart             # fast | smart
inputs:
  - {name: alert, type: textarea, label: Paste the alert}
  - {name: logs, type: file, accept: ".log,.txt,.csv", optional: true}
  - {name: asset, type: select, options: data/assets.csv, optional: true}
knowledge: knowledge/    # the team's runbooks
output: json             # stream | json | chat
answer: [score, table, checklist]   # blocks the model's JSON fills
examples:
  - label: Password spray, then a login
    inputs: {alert: "212 failed VPN logins for 9 users from 203.0.113.45, then a success for j.ortiz at 02:14"}
```

> [Image: Alert Triage screen — embed node/7cd6acee-b97a in the original doc]

The brand, screens and inputs come from the two files. The Air-gap capable badge, privacy note and response route appear on every screen with no code at all.

Every screen uses one of three layouts:

| Layout | Shape | Fits | Example in the repo |
|---|---|---|---|
| Workspace | Inputs on the left, a streamed answer on the right | Diagnose, draft, rewrite, summarize | Line Assist, manufacturing |
| Review | A file in; a score, a ranked table and a chart out | Audits, checks, analysis | Alert Triage, security operations (the lead) |
| Assistant | Chat with sources, phone first | Questions on the floor or in the field | Floor Help, retail |

The building blocks are everything a prompt can add. Each has a recipe in the OpenClaw skill and a check in `make check`.

| Kind | Blocks |
|---|---|
| Inputs | text, long text, select, number, toggle, file (TXT, CSV and PDF become text), image (read by the smart tier), example chips |
| Answers | streamed text, ranked list, checklist, table, score bar, bar or line chart, citations, follow-up chat |
| Actions | copy, download as Markdown or CSV, print, keep a history on this device |
| Trust signals | Air-gap capable badge, privacy note, response route and the How this runs panel, on every screen automatically |

| Tier | What it adds | Example | Platform changes |
|---|---|---|---|
| 1 Prompt | `app.yaml`, one screen and its prompt | Plain-language discharge (catalog) | None |
| 2 Knowledge | + `knowledge/` and `data/` | Line Assist, Floor Help | None |
| 3 Logic | + `hooks.py` and an answer schema | Alert Triage | None |
| 4 New model | a speech-to-text endpoint | Clinical Note Drafter with dictation (catalog) | Once, in the platform |

Each screen's examples do double duty: they are the example chips in the UI and the test cases `make check` runs.

## Visual design

The app design lives on its own canvas, base-app UI. It shows the placeholder, the lead app, Alert Triage, and two more apps built from the same parts, plus the How this runs panel.

| Element | Choice | Why |
|---|---|---|
| Brand | Each app sets its name, mark and one brand color in `app.yaml` | Every team's app looks like its own product |
| Shared parts | Header, forms, answers, tables, charts and trust signals come from the platform | Apps stay polished and consistent whatever OpenClaw writes |
| Type | Atkinson Hyperlegible Next, with its Mono for configs and code, vendored into the image | Designed for legibility, so it reads at a glance on a plant floor or in a store |
| Neutrals | Mineral gray `#ECEFF3` ground, white panels, slate ink `#17202B` | Calm, so the brand color and the answer stand out |
| Status | Verified `#0E7A5F` and check failed `#A85B00`, each with its own icon | Color is never the only cue |
| Signature | The response route under each answer: device, app and model server inside the site boundary, with measured times | Shows where each answer ran and how fast |

## OpenShift footprint and build loop

One base image serves every team's app, so each node pulls the platform once and a new app adds only kilobytes. Pods are stateless, request 64 MiB, and the app inside starts in about half a second. At that size, 100 app pods reserve roughly 6.25 GiB of memory and 2.5 CPU cores.

### Images

- **Base image, base-app:** Red Hat's minimal Python 3.12 runtime (`ubi9/python-312-minimal`) plus the pinned dependencies, the platform, its fonts and static assets. It uses the standard two-stage build: install the virtualenv in the full builder image, copy it into the minimal runtime. Rebuilt only when the platform changes.
- **App image:** FROM base-app plus `COPY app/`. That layer is the size of the folder, so a rebuild takes seconds and every node already caches the rest. Each team namespace runs one Deployment of its own app image.

| Pod setting | Default | Why |
|---|---|---|
| Port | 8080 | Non-root containers cannot bind ports below 1024 |
| User | Arbitrary UID in group 0 | The restricted-v2 SCC assigns a random UID; app files are group-0 owned |
| Filesystem | Read-only root, emptyDir at `/tmp` | Nothing persists inside the pod |
| Workers | 1 uvicorn worker; scale with replicas | Async I/O already handles many concurrent token streams |
| Requests / limits | CPU 25m, memory 64 MiB / CPU 500m, memory 256 MiB | 40 MB measured idle, with headroom for parsing PDFs and CSVs |
| Probes | Readiness and liveness on `/healthz` | Ready in about 0.5 s |

### The build and deploy loop

1. `make dev` runs the app on the user's VM with live reload against the dCloud model endpoints, so iterating needs no container build.
2. `make check` validates the app against a mock model (see Working with OpenClaw).
3. `git push` sends the change to the team's Gitea repo; the existing workflow builds the root Containerfile and rolls out the team's Deployment.
4. `make wait` polls the team's Route until `/api/version` reports the pushed commit, then `make smoke` runs every screen's examples and prints time to first words and total time.

The repo builds from a plain Containerfile at its root, so the workflow needs nothing specific to base-app. If the workflow is still to be built, the lightest version is a BuildConfig per team triggered by a Gitea webhook, plus an image-change trigger on the Deployment.

Optional scale-to-zero: with OpenShift Serverless (Knative Serving) installed, idle apps drop to zero pods and wake on the first request. Plain Deployments stay the default because they need no extra operator.

## Model tier

The models already run in dCloud, so the app needs only their OpenAI-compatible URLs, and every app pod shares them. The fast tier, Llama 3.1 8B, runs on its own hardware there. The smart tier is Nemotron 3.5 Super, released October 14, 2026: NVIDIA reports 51.8% on SWE-bench Pro, ahead of its larger Nemotron 3 Ultra, and it reads images, so image inputs need no separate vision model.

| Tier | Model | Used by | Hardware |
|---|---|---|---|
| smart | Nemotron 3.5 Super VL 120B-A12B: 120B total, 12B active, hybrid Mamba-Transformer MoE that reads text, images and video, up to 1M tokens of context | OpenClaw, screens marked smart (long documents, multi-step reasoning) and screens that take images | Four RTX PRO 6000s (96 GB each) in two hosts: one replica per host, split across its two cards |
| fast | Llama 3.1 8B Instruct | Most screens: short prompts, streamed answers, JSON extraction | Its own GPU in dCloud, separate from the four RTX PRO 6000s; about 16 GB of weights in BF16 |
| optional | A speech-to-text model | Tier 4 apps only | Add when GPUs allow |

- **Serving:** plain vLLM, Red Hat AI Inference Server (Red Hat's supported vLLM build, included in OpenShift AI) or NVIDIA NIM. All expose `/v1/chat/completions`, so the app cannot tell them apart.
- **Sharing:** vLLM batches concurrent requests from every pod onto the same GPUs, so adding app pods never adds a model copy.
- **Reasoning switch:** Nemotron 3.5 Super reasons before answering by default. The platform turns reasoning off through its chat template for screens marked `reasoning: off`, so the first visible token arrives sooner. The serve command below sets the reasoning and tool-call parsers.
- **Structured output:** json screens send a JSON schema built from their answer blocks as the response format. vLLM constrains decoding to it, so even the fast model returns JSON that parses.
- **Configuration:** seven environment variables, set once per team namespace: the model endpoints plus a default site name for the trust signals.

```bash
LLM_FAST_URL=http://vllm-fast.models.svc:8000/v1
LLM_FAST_MODEL=meta-llama/Llama-3.1-8B-Instruct
LLM_SMART_URL=http://nemotron-super.models.svc:8000/v1
LLM_SMART_MODEL=nvidia/nemotron-3.5-super
LLM_API_KEY=                 # optional
LLM_MOCK=0                   # 1 = canned streamed answers, no GPU (tests, dry runs)
SITE_NAME="dCloud lab"       # default site in the trust signals; app.yaml can set its own
```

### Serving Nemotron 3.5 Super on four RTX PRO 6000s

Run two replicas, one per GPU host, each split across that host's two cards (tensor parallel 2). Nothing crosses between hosts, and either host can go down without an outage. The four cards also hold two copies of the weights instead of four, which leaves far more memory for long prompts and many users at once.

| Layout | Weight copies | Context per request | One host down | Verdict |
|---|---|---|---|---|
| Two replicas, NVFP4, each on one host's two cards | 2 | About 114K tokens, vLLM's two-card setting for 80 GB H100s; these cards have 96 GB | The other replica serves | Use this |
| Four replicas, NVFP4, one card each | 4 | 16K tokens in vLLM's single-card RTX PRO 6000 setting, too short for OpenClaw's coding sessions | Two replicas serve | Avoid |
| BF16, one replica per host | 2 | Does not fit: about 240 GB of weights per copy, against 192 GB per host | Not applicable | No |
| One replica across both hosts | 1 | Largest | Nothing serves | Avoid: every token crosses the network |

Each RTX PRO 6000 has 96 GB on PCIe 5.0, and its datasheet lists no NVLink, so a host's two cards share the work over PCIe; across hosts, that traffic would go over the network. NVIDIA reports that the NVFP4 checkpoint keeps 99.6% of BF16 accuracy across 36 benchmarks while running 2.4 times faster.

```bash
# On each GPU host: one replica across both cards (vLLM 0.31 or later)
vllm serve nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-NVFP4 \
  --served-model-name nvidia/nemotron-3.5-super \
  --trust-remote-code \
  --tensor-parallel-size 2 \
  --max-model-len 114688 \
  --speculative-config.method mtp \
  --speculative-config.num_speculative_tokens 3 \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_coder \
  --reasoning-parser nemotron_v3
```

These flags come from vLLM's recipe for this model, with the context length of its two-card setting; add the recipe's Mamba cache settings for the vLLM version you run. Load-test with the lab's number of agents and app users before the event.

On OpenShift, one Deployment with `replicas: 2` and `nvidia.com/gpu: 2` per pod puts one pod on each host, since each host has two GPUs. Set `sessionAffinity: ClientIP` on the nemotron-super Service, so each user's OpenClaw keeps reaching the replica whose prefix cache already holds its conversation. With all four cards on Super, the fast tier points at it too unless the 8B model has a GPU of its own.

## Working with OpenClaw

OpenClaw gets a narrow lane: it edits only `app/`, runs the Makefile targets and pushes to its team's Gitea repo. Small files, one obvious place to work and a fast, exact test command are what keep a 120B open model productive.

**How AGENTS.md gets into OpenClaw.** OpenClaw has one home folder, called its workspace. At the start of every chat it opens the AGENTS.md in that folder and adds its text to the instructions it sends the model. It never looks for an AGENTS.md anywhere else, not even in a folder it is editing. Out of the box the workspace is `~/.openclaw/workspace`, where OpenClaw writes a starter AGENTS.md of its own (agent workspace).

So nothing is copied. Instead, the workspace becomes the user's clone of the team repo, which already holds the rules. Step by step:

1. **The repo carries the rules.** Every team repo starts from the base-app template, which holds `AGENTS.md` and `skills/base-app/SKILL.md` beside `app/`.
2. **Provisioning clones the repo.** Before the user signs in, the lab's VM setup installs the latest stable OpenClaw and clones the team repo, with its push credentials, to `~/team-07-app`.
3. **Provisioning points OpenClaw at the clone.** The same setup writes OpenClaw's config file, shown below: the workspace is `~/team-07-app`, OpenClaw skips its starter files because the repo has its own, and the model is Nemotron 3.5 Super (workspace and bootstrap settings, vLLM provider).
4. **Every chat reads the rules.** When the user starts a chat, OpenClaw reads `~/team-07-app/AGENTS.md` into its instructions and lists the skills in `~/team-07-app/skills/`, opening a full SKILL.md when a task needs it (skills). Its commands run in `~/team-07-app` too, so `make check` and `git push` work as written.
5. **Changes arrive with git.** To change the rules, commit a new AGENTS.md to the repo and run `git pull` on the VM. The next chat (`/new`) uses it; a changed skill applies from the next message.

```json5
// ~/.openclaw/openclaw.json, after: git clone <team-07 repo> ~/team-07-app
{
  agents: {
    defaults: {
      workspace: "~/team-07-app",   // the team repo is the workspace
      skipBootstrap: true,          // keep OpenClaw's starter files out of the repo
      model: { primary: "vllm/nvidia/nemotron-3.5-super" },
    },
  },
  models: {
    providers: {
      vllm: {
        baseUrl: "https://SMART_TIER_HOST/v1",   // the smart tier, as the VM reaches it
        apiKey: "${VLLM_API_KEY}",
        api: "openai-completions",
        models: [{ id: "nvidia/nemotron-3.5-super", input: ["text", "image"], contextWindow: 114688 }],
      },
    },
  },
}
```

The repo's `.gitignore` leaves out `memory/` and `MEMORY.md`, where OpenClaw keeps its own notes.

The repo's AGENTS.md, kept short on purpose:

```markdown
# base-app rules
1. Your app is app/. Edit nothing outside it.
2. Start from the user's idea or a brief in catalog/. Copy patterns from examples/.
3. Every screen uses one layout: workspace, review or assistant.
4. Hooks use only the Python standard library and the ctx helpers. No new packages.
5. Sample data is synthetic. Never paste real customer, patient or employee data.
6. No network calls and no external URLs, in code or in HTML.
7. If no building block fits a request, say so and suggest the closest one.
8. Run make check after every change. Do not push until it passes.
9. Push to your team repo (see team.env), run make wait and make smoke, and report the timings.
```

### The loop OpenClaw runs

1. Read the user's idea or the named brief, and the example with the same layout.
2. Write `app.yaml`, the screen, its prompt and synthetic data.
3. Run `make check` and fix whatever it names.
4. Run `make dev`, call an example through the API and read the answer.
5. Commit and `git push` to the team repo, then run `make wait` and `make smoke` against the team's Route.

Each team repo carries a `team.env` with the team number, the Gitea remote and the app's Route, so OpenClaw always pushes to the right repo and tests the right URL. The app's `/api/version` reports the running commit, which is how `make wait` knows the new build is live.

What `make check` does, in under 5 seconds with no GPU:

- Validates `app.yaml` and every screen against the schema, including the brand color's contrast with white text.
- Renders each prompt with the example inputs and flags undefined variables.
- Imports `hooks.py` and runs it on the examples.
- Renders every screen and runs every example end to end against the mock model.
- Fails if `platform/` differs from the pinned version, so a stray edit is caught before it ships.

Errors name the file, the field and the fix, because that is what a model can act on: `app/screens/ask.yaml: inputs[2].type "dropdown" is not valid; use one of text, textarea, select, number, toggle, file, image.`

### Guardrails on the cluster

- OpenClaw needs no cluster credentials at all. Its only write access is `git push` to its own team repo; the workflow does the building and deploying.
- OpenClaw runs shell commands and edits files on its own, and its non-interactive setup requires an explicit accept-risk flag. The per-user lab VM is the right place for it; keep real credentials off it.

## The prompt ladder

Two or three prompts build a working prototype, and every later prompt adds one building block. Lab users type them, and they need not be technical, so each prompt is plain language and the guide page gives basic instructions around it. The guide page will hold the final wording; these show the shape.

1. **Build:** "Build the Alert Triage app from catalog/it-alert-triage.md for the HQ security team." Or a team's own idea: "Build an app for store associates that answers stock and returns questions from our inventory export and returns policy." OpenClaw writes `app.yaml`, the first screen, its prompt and synthetic data, then checks, pushes and reports the app's URL.
2. **Ground it:** "Add our three runbooks to the knowledge folder and cite the step behind each action." Or "Make the sample data realistic: a week of VPN, firewall and sign-in logs for 40 users."
3. **Shape the answer:** "Show a severity score, a table of attack techniques and a checklist of next steps."

After that, one prompt per feature:

| Prompt | Building block |
|---|---|
| "Add a chart of failed logins by hour." | Bar chart over numbers a hook computes |
| "Let analysts ask follow-up questions." | Follow-up chat |
| "Add a Download as Markdown button for the incident ticket." | Download action |
| "Add a screen for the shift lead that summarizes the day's alerts." | New screen, workspace layout |
| "Use the fast model, with reasoning off, for a quick first look." | Model tier |
| "Keep a history of past triages on this device." | History action |
| "Let analysts paste a screenshot of the alert console." | Image input, read by the smart tier |

Each prompt changes one block, so `make check` can test it and the push stays small. When a prompt asks for something no block covers, OpenClaw says so and suggests the closest block instead of editing the platform.

## Why local: six reasons

Every idea in the catalog rests on at least two of these reasons, and its brief lists them. In the finished app they are not slogans: the trust signals below make them visible.

| Tag | Reason | What it means in practice |
|---|---|---|
| `ip` | Sovereign data and IP | Designs, recipes, prices, plans and customer records never leave the company, and no third-party processor has to be trusted |
| `regulated` | Regulated data | Patient (HIPAA), cardholder (PCI DSS), export-controlled (ITAR/EAR) and grid (NERC CIP) data stay inside a boundary you already audit |
| `latency` | Latency | No WAN round trip and no public queue: the answer arrives while the person is still at the machine, counter or bedside |
| `offline` | Disconnected operation | Plant floors, stores, ships, field sites and classified enclaves keep working when the WAN is down, or where there never was one |
| `volume` | Cost at volume | Repetitive, high-volume work (every SKU, alert or ticket) runs on a fixed GPU instead of a per-token bill |
| `pinned-model` | Model control | Open weights pinned to a version cannot change under you, so outputs can be reproduced, audited and validated |

Honest framing for the lab: cloud AI services can be made compliant. Running locally removes the third party instead of managing it, and that is what each app demonstrates.

## Trust signals: measured, not claimed

Every app makes the case for running on-site in its own interface, not in marketing copy: a badge, a note and a timed route on every screen. The badge and the note state what the design guarantees; the route and the speeds are measured live.

| Signal | Where it appears | What it says | What backs it |
|---|---|---|---|
| Air-gap capable badge | App header, every screen | Air-gap capable | The design: the model, data, code and fonts all run on-site, and `make check` rejects any external URL |
| Privacy note | Under inputs and uploads | Alerts stay in the HQ data center | The site in `app.yaml`; the app sends data only to its own model endpoints |
| Response route | Under every answer | Answered on-site in 0.42 s, with the path from device to app to model server | Browser timing for device to app; the app times its own model calls, the first words and the finish |
| How this runs panel | Opened from the badge | Where each part runs, what the app needs from the internet (nothing) and speed this session | The site, the model name and pinned version from the model server, and the timings above |

Wording rules: the badge says Air-gap capable, meaning the app can run with no internet connection. It never claims the site itself is air-gapped, it makes no comparisons with cloud services, and every speed it shows is measured.

## Use case catalog: manufacturing, retail, healthcare

Twelve ideas cover the three requested industries. Each ships as a one-page brief in `catalog/` that a team's first prompt can name, and two of them, Line Assist and Floor Help, are built as examples.

### Manufacturing

| Use case | What it does | Why it runs local | Model | Tier |
|---|---|---|---|---|
| Line-Side Maintenance Copilot (example: Line Assist) | A technician enters the machine, symptoms and alarm log, and gets ranked causes, checks, parts and safety steps from the plant's own manuals | Plant control networks are walled off from the internet, the manuals and settings are IP, and a stopped line cannot wait on a WAN | fast | 2 |
| 8D Quality Report Writer | Turns inspection data and operator notes into a structured 8D report: containment, five-why root cause, corrective actions | Defect and yield data reveal process capability and supplier problems, some of the most guarded numbers in a plant | smart | 3 |
| Work Instruction Builder | Converts engineering changes and specs into step-by-step, multilingual work instructions for the floor | Designs are crown-jewel IP, and for defense suppliers they are export-controlled technical data (ITAR/EAR) | smart | 1 |
| Visual Defect Inspector | Classifies a photo of a part against the plant's defect catalog and explains what it sees | Product images are IP, volumes are high, and inspection has to keep pace with the line | smart | 3 |

### Retail

| Use case | What it does | Why it runs local | Model | Tier |
|---|---|---|---|---|
| Store Associate Copilot (example: Floor Help) | Answers product, policy and stock questions on the shop floor from the store's catalog, policies and inventory export | Runs at the store edge and keeps working when the store's link drops; prices and stock levels are competitive data | fast | 2 |
| Shrink and Exceptions Analyst | Reads a point-of-sale exceptions export (voids, refunds, no-sales), computes KPIs and ranks patterns worth a review | Transaction and employee data stay in-house, which keeps PCI DSS scope and employee-privacy exposure small | fast | 3 |
| Product Content Factory | Writes a product description, attributes and translations from a supplier spec sheet, one SKU per run | Unreleased products must not leak before launch, and at catalog scale a fixed GPU beats per-token pricing | fast | 1 |
| Clienteling Assistant | Drafts personal outreach and product suggestions for a store stylist from a customer's purchase history | Purchase histories are personal data and the retailer's most valuable first-party asset | fast | 3 |

### Healthcare

| Use case | What it does | Why it runs local | Model | Tier |
|---|---|---|---|---|
| Plain-Language Discharge Instructions | Rewrites a discharge summary as plain-language instructions at a chosen reading level and language | Protected health information never leaves the hospital network, so there is no outside processor to contract and audit | fast | 1 |
| Clinical Note Drafter | Turns a visit transcript into a SOAP note and a patient summary, with suggested codes flagged for review | The most sensitive PHI there is, and it must keep working through internet outages, between patients | smart | 3 (4 with speech-to-text) |
| Prior Authorization Letter Assistant | Drafts the medical-necessity letter from chart notes and the payer's criteria | PHI plus negotiated payer documents, at a volume where per-token pricing adds up | smart | 2 |
| Clinical Trial Pre-Screener | Checks a patient summary against a trial's inclusion and exclusion criteria and marks each one met, not met or unknown | Patient records and unpublished trial protocols, which are sponsor IP, both stay inside | smart | 3 |

## Use case catalog: five more industries

Fifteen more ideas fit the same platform unchanged. IT and network operations is the natural opener for a Cisco dCloud audience, because every attendee has configs and logs they could never paste into a public AI service. It also holds the lead, Alert Triage.

### IT and network operations

| Use case | What it does | Why it runs local | Model | Tier |
|---|---|---|---|---|
| Alert Triage (the lead) | Turns a security or network alert and its logs into a verdict, a severity, a timeline and next steps from your runbooks | Logs map the network, its users and its weak spots; containment or an outage can cut the internet link; every alert gets read in full at no extra cost | smart | 3 |
| Network Config Auditor | Checks a router or switch config against your hardening baseline and returns the exact remediation lines | Configs hold credential hashes, SNMP strings and the full topology; pasting them into a public AI service is a security incident | smart | 2 |
| Change Plan (MOP) Writer | Drafts a method of procedure with pre-checks, rollback steps and a risk rating from a change request | Change plans reveal infrastructure layout and maintenance windows | smart | 3 |

### Financial services

| Use case | What it does | Why it runs local | Model | Tier |
|---|---|---|---|---|
| AML Alert Narrator | Summarizes a transaction-monitoring alert with the customer's profile and history, then drafts the disposition or SAR narrative | Customer financial data, and the existence of a SAR must stay confidential | smart | 3 |
| Credit Memo Drafter | A hook computes ratios from the financial statements; the model writes the credit narrative around them | Borrower financials are confidential, and a pinned open model is easier to validate under model-risk rules | smart | 3 |
| Complaint Triage | Classifies complaints by product and regulatory category, extracts entities and suggests routing | Thousands a day, full of personal data; schema-constrained JSON lets the fast model do it at a fixed cost | fast | 3 |

### Public sector and defense

| Use case | What it does | Why it runs local | Model | Tier |
|---|---|---|---|---|
| Records Release Redaction Assistant | Flags personal and exempt information in documents before public release and suggests redactions with reasons | The documents hold exactly the data that must not leave the agency | smart | 3 |
| Disconnected Field Report Summarizer | Turns raw field reports into structured situation reports at the edge | Classified networks are air-gapped, and field kits run disconnected | fast | 1 |
| Caseworker Policy Assistant | Answers eligibility questions from the agency's policy manuals and drafts letters to citizens | Citizen identity and income data, plus data-residency rules, keep this inside the agency | fast | 2 |

### Energy and utilities

| Use case | What it does | Why it runs local | Model | Tier |
|---|---|---|---|---|
| Alarm Flood Summarizer | During an event, groups hundreds of SCADA alarms into the likely initiating event and the next checks | Control systems sit behind NERC CIP security perimeters, and seconds matter in an alarm flood | fast | 3 |
| Field Crew Safety Briefing | Generates the pre-job hazard briefing from the work order and site conditions | Runs on edge hardware at remote sites with no connectivity | fast | 1 |
| Inspection Report Drafter | Drafts pipeline, substation or plant inspection reports from inspector notes and readings | Vulnerability details of critical infrastructure must stay with the operator | smart | 2 |

### Legal and professional services

| Use case | What it does | Why it runs local | Model | Tier |
|---|---|---|---|---|
| Contract Clause Reviewer | Extracts key clauses into a table and flags deviations from the firm's playbook | Privileged client documents; sending them to a third party puts privilege and the client relationship at risk | smart | 3 |
| Deposition Summarizer | Summarizes long transcripts with page and line references | Privileged material, and long transcripts suit the smart model's long context window | smart | 1 |
| Deal Room Q&A | Answers questions over a data room with citations to the source documents | Material non-public information: a leak can move a share price | smart | 2 |

## What ships in each team repo

Each repo starts with a placeholder app, three finished examples and the catalog briefs. The examples double as the platform's end-to-end tests.

| Item | What it is | Why it is there |
|---|---|---|
| Placeholder app | A plain screen saying the app will appear here, with live health checks | Proves push, build, deploy and model access before the first prompt |
| Alert Triage (the lead) | Review layout, security operations, smart model | Pattern for a log upload, knowledge search, a score bar, a table and a checklist |
| Line Assist | Workspace layout, manufacturing, fast model | Pattern for inputs, knowledge search and a streamed answer |
| Floor Help | Assistant layout, retail, phone first | Pattern for chat with sources |
| 27 catalog briefs | Persona, problem, data, reasons to run locally, suggested layout | Starting points for prompt 1 |

Acceptance checks for the platform:

- `make check` passes against the mock model in under 5 seconds.
- On a fresh team namespace, the placeholder shows every health check passing.
- All three examples run end to end against the dCloud models through `make smoke`.
- An idle pod stays under its 64 MiB request and starts in under 1 second.
- A one-line change is live within a minute of the push.
- OpenClaw builds Alert Triage from its catalog brief in three prompts, using only the skill and AGENTS.md.

## Next steps

1. You review the lead app, Alert Triage, on the canvas.
2. I build the platform, the placeholder, the three examples, the catalog briefs, the OpenClaw skill and make check.
3. You run it on the cluster, and we record real footprint and timing numbers against the acceptance checks.
4. I build the guide page: the prompts that build Alert Triage, then one prompt per feature.

## Sources

- NVIDIA Nemotron 3.5 Super and Lightning, NVIDIA Research
- Nemotron 3.5 Super VL NVFP4 serving recipe, vLLM recipes, including the RTX PRO 6000 and two-card settings
- NVIDIA RTX PRO 6000 Blackwell Server Edition datasheet, NVIDIA, hosted by Akamai
- Agent workspace, OpenClaw docs
- Workspace and bootstrap settings, OpenClaw docs
- Skills, OpenClaw docs
- vLLM provider, OpenClaw docs
- The State of AI in the SOC 2025, The Hacker News, a survey of 282 security leaders
- Ransomware Response Checklist, CISA
- ubi9/python-312-minimal, Red Hat Ecosystem Catalog
- Red Hat AI Inference Server technical deep dive, Red Hat blog
- Memory and startup figures: measured by Claude on 2026-11-23 on a test VM with a minimal Starlette, uvicorn and Jinja2 server.
