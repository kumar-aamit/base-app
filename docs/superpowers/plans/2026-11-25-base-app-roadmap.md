# base-app Roadmap

**Spec:** `base-app/base-app-paper.md`

base-app replaces the `openclaw-demo/team-app` template (Machine Downtime Log). It plugs into the existing pipeline unchanged in shape: `start-lab.sh` bootstraps each team namespace and seeds the team repo through the Gitea Contents API; each push runs Gitea Actions, which runs `oc start-build --from-dir=.` against the team's Docker-strategy BuildConfig.

Each phase is its own plan and ends with software that runs.

| Phase | Builds | Proves (acceptance checks from the spec) |
|---|---|---|
| 1. Skeleton to cluster | `baseapp` package with config, `app.yaml` loading, placeholder page with live health checks, trust header, `/api/version`; base image; team template (`Dockerfile`, `Makefile` with `dev` and `wait`, `team.env`); `openshift-automation` and `start-lab.sh` changes | Placeholder shows every check passing on a fresh namespace; idle pod under 64 MiB and ready in under 1 s; a one-line change is live within a minute of the push |
| 2. Screen engine and Review layout | Screen schema, prompt rendering, model client (stream, json with schema, mock), file inputs (TXT, CSV, PDF), BM25 knowledge, `hooks.py` with `ctx`, score/table/checklist blocks, response route timing, How this runs panel, `make check`, `make smoke`, the Alert Triage example | `make check` passes against the mock model in under 5 s; Alert Triage runs end to end against the dCloud models |
| 3. Workspace and Assistant layouts, remaining blocks | Streamed text, ranked list, bar and line charts, citations, follow-up chat, copy/download/print/history actions, image input, example chips; Line Assist and Floor Help examples | All three examples run end to end through `make smoke` |
| 4. OpenClaw lane | `AGENTS.md`, `skills/base-app/SKILL.md` with one recipe per block, 27 catalog briefs, `openclaw.json` provisioning on the user VM, `platform/` pin check in `make check` | OpenClaw builds Alert Triage from its catalog brief in three prompts |
| 5. Guide page | The prompt ladder for lab users | A non-technical user follows it to a working app |

Out of scope for every phase: serving the models. The fast and smart endpoints already run in dCloud.

Decisions taken before planning (from the user):

- The dCloud lab-start automation builds and deploys the base image. Phase 1 adds that step to `bootstrap-openshift-cicd.sh`, which `start-lab.sh` already runs.
- Port stays 8742 and `/health` keeps working, so existing Services and Routes are unchanged. `/healthz` is added as the paper describes.
- Both a fast and a smart endpoint run today; each namespace gets both URLs.
