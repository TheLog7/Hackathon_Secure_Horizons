# Demo script — Secure Horizons

The pitch in one line: **an NDR that reads the calendar.** It doesn't just learn how people
behave — it learns *why*, so it clears context-justified anomalies and catches the ones with
no cover story.

## Setup (3 terminals + 1 for seeding)

```bash
source .venv/bin/activate
python -m scripts.seed_data                                    # once

python -m uvicorn services.engine.main:app       --port 8000  # terminal 1
python -m uvicorn services.user_service.main:app --port 8100  # terminal 2
python -m uvicorn services.admin.main:app        --port 8200  # terminal 3
```

Open the **admin console** (http://localhost:8200) on the projector and the
**employee endpoint** (http://localhost:8100) on your laptop.

## Act 1 — "looks bad, but the agenda clears it"

1. Employee endpoint → select **Alice Moreau (Finance)**.
2. Point out her agenda: *Q3 financial close audit, 01:00–04:00*.
3. Click **"Access finance DB — 02:10"** (amber / context).
4. Admin console shows a **NORMAL** verdict, green, tagged **✅ Agenda-justified**.
   > A classic NDR would page the SOC at 2 a.m. for this. Ours reads the calendar and stays quiet.

## Act 2 — the wrong action → ALERT

1. Employee endpoint → select **Dan Weber (Engineering)**.
2. Note Dan has **never** touched `customer-db` and has no evening agenda entry.
3. Click **"Exfiltrate customer database — 21:50"** (red / malicious).
4. Admin console lights up: **ANOMALY · CRITICAL**, red, **⚠ No agenda justification**, with
   Claude's reasoning (off-hours + unusual resource + 240 MB to an external IP) and a
   "isolate the endpoint" recommendation — appearing live within a second.

## Optional extra beats

- **Raj (IT)** "Server patch + reboot — 02:30" → cleared (patch window in agenda), showing the
  model doesn't just whitelist IT blindly; it checks the *scheduled window*.
- **Raj** "Create hidden admin account — 03:10" → anomaly: privileged change with no change ticket.
- **Mia (Sales)** "Update CRM from Berlin" (external IP) → cleared by the *Client visit* agenda,
  vs. **"Bulk-export entire CRM"** → anomaly.
- **Tom (Marketing)** "Access finance DB" → anomaly purely on baseline (marketing never touches finance),
  even though it's during business hours.

## Talking points

- The agenda is the **ground truth of intent** that log-only NDR lacks → fewer false positives.
- Swap the stub for the **real Claude model** on Bedrock by setting `USE_REAL_BEDROCK=true`;
  the reasoning text then comes straight from Sonnet 5.5.
- Three separate services = three "machines"; move each to its own VM/container with no code change.
