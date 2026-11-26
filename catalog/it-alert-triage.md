# Alert Triage

**Industry:** IT and network operations · **Layout:** review · **Model:** smart · **Tier:** 3 (hooks and an answer schema)
**Reasons to run on-site:** `volume`, `ip`, `regulated`, `latency`, `offline`, `pinned-model`

## Who uses it
A security analyst on the HQ security team, working the alert queue during a shift.

## The problem
The team gets hundreds of alerts a day and cannot read every one with its logs. Pasting alerts and
logs into a public AI service is not allowed: they map the network, its users and its weak spots.

## What the app does
The analyst pastes an alert, attaches its logs and picks the affected system. The app returns:
- a severity score from 0 to 100 with a one-line label
- a verdict: what most likely happened and why, quoting the log lines that matter
- a table of MITRE ATT&CK techniques the evidence supports
- a checklist of next steps, each citing the runbook step it came from

## Data to make up
- `data/assets.csv`: about six systems with hostname, role, owner, criticality and location
- a VPN log with a password spray from one outside address and one success afterwards
- a VPN log with a single locked-out user who was reset by the help desk (the benign case)
- `knowledge/`: three short runbooks with sections Signs, Contain, Investigate and Escalate or Recover:
  password spray, reported phishing email, suspected malware beacon

Use documentation address ranges (192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24) and `.example`
domains. Invent every name.

## Examples to include
1. Password spray, then a login (should score 80 or more)
2. Reported phishing email, no logs (should score in the middle)
3. Locked-out user, already reset (should score under 40)

## Build it in three prompts
1. **Build:** app.yaml, the screen with alert, logs and asset inputs, a text verdict, the asset list and the spray log.
2. **Ground it:** the three runbooks in knowledge/, and a checklist of next steps that cites them.
3. **Shape the answer:** a severity score, a table of techniques, and hooks.py to count the failed logins exactly.

## Prompts to send
Send these to the agentic harness one at a time. After each one, it runs `make check`, pushes, and
reports the app URL and timings; open the URL and click an example before sending the next.

1. Build the Alert Triage app from catalog/it-alert-triage.md for the HQ security team.
2. Add our three runbooks to the knowledge folder and cite the step behind each action.
3. Show a severity score, a table of attack techniques and a checklist of next steps. Count the
   failed logins exactly instead of letting the model guess, and add the locked-out user who was
   already reset as a low-severity example.

After that, one prompt per change, for example:
- Use the fast model, with reasoning off, for a quick first look.
- Rename the app to SOC Triage and make the brand color darker.
