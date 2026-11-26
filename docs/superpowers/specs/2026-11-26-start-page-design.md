# Start page design

Replaces the placeholder ("Your app will appear here") with a start page that hands each lab user
the next prompt. Reviewed from the mockup `Base App Start Page.html`; approved 2026-11-26 with the
core scope, all ten use cases, a footer link back and a `LAB_USER` label.

## What it shows

- **What do you want to build?** with a live check strip: App, Fast model, Smart model. Anything not
  green says why in words; a failing model adds "Tell the lab staff".
- Ten use-case chips. Alert Triage is first and marked "3 prompts"; eight more have one detailed
  prompt each; "Your own idea" is a text box.
- Left: step tabs (Alert Triage only), the prompt, **Copy prompt N**, and what to try once it is live.
- Right: a preview of the screen the prompt builds: its inputs and the answer blocks, with the
  blocks this prompt adds outlined. "On your app now" once the step is built.
- Limits: text, score, table and checklist; not yet charts, chat or images.

## Where it lives

- `/` shows it while `app.yaml` has no screens; after that `/` opens the first screen as before.
- `/start` always shows it. Every page's footer links to it.
- Use cases and prompts: `platform/baseapp/usecases.yaml`, in the base image, because `catalog/`
  is not copied into the app image. A test keeps Alert Triage's prompts identical to its brief.

## What is real, and what was dropped

- Steps tick from what the loaded app has: step 1 a screen; step 2 `knowledge:` and a checklist;
  step 3 a score and a table. The tab for the next step is selected by default.
- The page polls `/api/version` every 5 s and reloads when the commit changes. If the user has typed
  their own idea, it says a new build is live instead of reloading.
- Dropped from the mockup: harness progress chips (the app cannot see the harness), "Improve with
  fast model" (a new model call; later), simulated timings, and Google Fonts (bundled Atkinson
  Hyperlegible instead).

## Server-rendered

Chips and step tabs are links (`/start?case=config&step=2`). `static/js/start.js` only copies the
prompt (with a select-to-copy fallback), checks the own-idea text (who, what they enter, what they
get, unsupported words, which blocks to preview) and polls for a new build.

## Lab user label

`LAB_USER` in the environment shows `· user-7` beside the app name in the header. `start-lab.sh`
sets it on each Deployment; unset, nothing shows.
