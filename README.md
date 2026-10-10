# Secure Horizons — Agenda-Aware NDR (mock)

A mock **Network Detection & Response (NDR)** platform whose "ML model" is played by a
**Claude model on AWS Bedrock**. The revolutionary twist: the detection engine doesn't just
learn each employee's behavioural baseline from 2 weeks of logs — it also reads their
**professional agenda**, so it understands *intent*. A 2 a.m. login to the finance server is
an anomaly... unless the calendar shows a scheduled overnight audit.

## Architecture

Three independent services that talk over HTTP, mirroring a real distributed NDR deployment.
They run as plain processes on one machine today, and could each move to their own VM/container
later with no code change.

```
┌─────────────────────┐      logs      ┌──────────────────────┐    alerts     ┌─────────────────────┐
│  USER SERVICE (VM2)  │ ─────────────▶ │  DETECTION ENGINE     │ ────────────▶ │  ADMIN CONSOLE (VM1) │
│  the employee        │   HTTP POST    │  "the NDR model"      │   SSE stream  │  SOC analyst console │
│  - holds the agenda  │                │  - behavioural base   │               │  - live alert feed   │
│  - performs actions  │                │  - Claude via Bedrock │               │  - reasoning + agenda│
│  - one "wrong action"│                │  - verdict + reason   │               │  - severity triage   │
└─────────────────────┘                └──────────────────────┘               └─────────────────────┘
```

| Service          | Port  | Role                                                                   |
|------------------|-------|------------------------------------------------------------------------|
| Detection engine | 8000  | Receives log events, loads baseline + agenda, asks Claude, stores verdict, streams via SSE |
| User service     | 8100  | Web UI to drive an employee and emit normal / malicious actions        |
| Admin console    | 8200  | Web dashboard showing the live event + alert stream                    |

## The Claude model

Default model: **Claude Sonnet 5.5** on Bedrock (`us-east-1`), configurable via `BEDROCK_MODEL_ID`.
The engine resolves a valid **cross-Region inference profile** from your account at startup
(falls back to the configured ID). A **stub mode** returns realistic verdicts with zero AWS
credentials so the app runs anywhere; set `USE_REAL_BEDROCK=true` to call the real model.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# generate the synthetic company (employees, 2 weeks of logs, agendas)
python -m scripts.seed_data

# run the three services (each in its own terminal)
python -m uvicorn services.engine.main:app --port 8000
python -m uvicorn services.user_service.main:app --port 8100
python -m uvicorn services.admin.main:app --port 8200
```

Then open:
- Admin console  → http://localhost:8200
- User service   → http://localhost:8100

### Enabling the real Claude model

```bash
export USE_REAL_BEDROCK=true
export AWS_REGION=us-east-1
# plus your AWS credentials (env vars, SSO, or a named profile)
export BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-5-5-20251101-v1:0   # adjust to a profile in your account
```

> Note: outbound Bedrock calls need network + AWS credentials, so run with `USE_REAL_BEDROCK=true`
> on your own machine. In stub mode no network is required.

## Demo flow

1. In the user service, pick **Alice (Finance)** and click **"Access finance DB — 02:10"**.
   Her agenda has a *Q3 audit, 01:00–04:00* → engine clears it as **NORMAL (context-justified)**.
2. Pick **Dan (Engineering)** and click the **"Exfiltrate customer database"** (the wrong action).
   No agenda justification, off-baseline → engine raises a **HIGH severity ANOMALY** that lights
   up red on the admin console in real time.

See `docs/` for the full scenario script.
