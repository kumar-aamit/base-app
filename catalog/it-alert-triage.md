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
Send these to the agentic harness one at a time, copying each block whole. Each one says
everything that step builds, so it works even if the harness does not reread this brief. After
each one, it runs `make check`, pushes, and reports the app URL and timings; open the URL and
click an example before sending the next. `GUIDE.md` has the same prompts.

### Prompt 1: Build

```text
Build an app called Alert Triage for the HQ security team. Use the shield mark, brand color
#1D4ED8 and site "HQ data center".

Give it one screen, "Triage an alert", in the review layout with the smart model. Inputs:
- "Paste the alert": long text
- "Attach the logs": an optional file (.log, .txt or .csv)
- "Affected system": an optional select filled from data/assets.csv
The answer is one text block, "Verdict": two or three sentences on what most likely happened,
how sure you are and why, quoting the log lines that matter with their timestamps.

Make up the sample data, using only 192.0.2.0/24, 198.51.100.0/24 and 203.0.113.0/24 addresses
and invented names:
- data/assets.csv with columns hostname, role, owner, criticality, location and six systems:
  vpn-gw-01 (VPN gateway), mail-01 (mail relay), dc-01 (domain controller), fin-db-02 (finance
  database), web-ext-01 (public website) and hr-laptop-114 (an HR laptop).
- data/vpn-spray.log, about 230 lines like
  "2026-11-24T01:52:08Z vpn-gw-01 auth user=a.chen src=203.0.113.45 result=FAIL reason=bad_password":
  normal logins from 198.51.100.x, then 212 failures for 9 users from 203.0.113.45 between 01:52
  and 02:12, then a success for j.ortiz from that address at 02:14:07 with mfa=none
  reason=legacy_client, and a connection from that session to fin-db-02 at 02:16:31.

Add two examples, each with a mock answer:
- "Password spray, then a login": the alert "212 failed VPN logins for 9 users from
  203.0.113.45, then a success for j.ortiz at 02:14", the spray log and vpn-gw-01.
- "Reported phishing email": the alert "m.reyes reported an email from
  payroll-update@examp1e-hr.example asking staff to confirm bank details through a link",
  no logs, and mail-01.
```

### Prompt 2: Ground it

```text
Add three runbooks to a knowledge/ folder, each a Markdown file with one # title and short
## sections:
- password-spray.md, "Runbook: password spray against VPN or single sign-on":
  Signs, Contain, Investigate, Escalate
- phishing.md, "Runbook: reported phishing email": Signs, Contain, Investigate, Recover
- malware-beacon.md, "Runbook: suspected malware beacon": Signs, Contain, Investigate, Recover

Search them on the triage screen. Add a checklist answer, "Next steps": at most six steps, in
the order the analyst should do them, each specific to this alert (name the address, account or
system) and citing the runbook passage it came from as [n]. Leave the source empty for a step no
runbook covers. Update both examples' mock answers with steps that cite passages the search
really finds.
```

### Prompt 3: Shape the answer

```text
Shape the triage answer into four parts, in this order:
- "Severity": a score from 0 to 100 with a one-line label. 80 or more means act now, 40 to 79
  means investigate today, under 40 means likely benign or already handled. Raise it when the
  affected system's criticality is high or critical.
- "Verdict": the text block you have now.
- "Attack techniques": a table with columns Technique, ID and Evidence, one row per MITRE
  ATT&CK technique the evidence supports.
- "Next steps": the checklist you have now.

Add hooks.py so the app counts before the model answers. From the attached log: the number of
failed logins, their time range, the accounts tried, failures by source address, and any
success from a failing address after the failures. From data/assets.csv: the affected system's
role, owner and criticality. Put both in the prompt and tell the model the counts are exact.

Add a third example, "Locked-out user, already reset": the alert "Account lockout for s.ito on
the VPN after 6 failed logins", vpn-gw-01, and a new data/vpn-lockout.log where s.ito fails 5
times from 198.51.100.23, is locked out at 09:00:16, the help desk resets the password at 09:21
after a callback, and s.ito logs in with MFA at 09:24. Its severity should be under 40. Update
all three mock answers to the new shape.
```

### After that, one prompt per change

- Use the fast model, with reasoning off, for a quick first look.
- Rename the app to SOC Triage and make the brand color darker.
