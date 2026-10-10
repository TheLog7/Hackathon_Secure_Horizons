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

## Quick start (Windows)

> Prerequisite: Python 3.11+ installed and on your `PATH`. Check with `python --version`.
> If `python` isn't found, try `py` (the Windows launcher) in place of `python` below.

### 1. Create a virtual environment and install dependencies

**PowerShell**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

> If PowerShell blocks the activation script with an execution-policy error, run once:
> `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`, then activate again.

**Command Prompt (cmd.exe)**
```bat
python -m venv .venv
.\.venv\Scripts\activate.bat
pip install -r requirements.txt
```

### 2. Seed the synthetic company (employees, 2 weeks of logs, agendas)

```powershell
python -m scripts.seed_data
```

### 3. Run the three services — each in its own terminal

Open **three** PowerShell/cmd windows, activate the venv in each (step 1's activate line),
then run one service per window:

```powershell
python -m uvicorn services.engine.main:app --port 8000
```
```powershell
python -m uvicorn services.user_service.main:app --port 8100
```
```powershell
python -m uvicorn services.admin.main:app --port 8200
```

Then open in your browser:
- Admin console  → http://localhost:8200
- User service   → http://localhost:8100

### Enabling the real Claude model

Set the environment variables in the **same terminal** where you launch the **engine**
(service on port 8000) *before* running it. Credentials are read by the AWS SDK (`boto3`) —
you never paste them into the code.

**PowerShell** (variables last for the current window only)
```powershell
$env:USE_REAL_BEDROCK = "true"
$env:AWS_REGION = "us-east-1"
# AWS credentials — use ONE of the following:
#  a) access keys:
$env:AWS_ACCESS_KEY_ID = "your-key-id"
$env:AWS_SECRET_ACCESS_KEY = "your-secret"
$env:AWS_SESSION_TOKEN = "your-session-token"   # only if using SSO / a temporary role
#  b) or a named profile (after `aws sso login` / `aws configure`):
# $env:AWS_PROFILE = "your-profile-name"

# adjust to an inference profile that exists in your account (see note below):
$env:BEDROCK_MODEL_ID = "us.anthropic.claude-sonnet-5-5-20251101-v1:0"

python -m uvicorn services.engine.main:app --port 8000
```

**Command Prompt (cmd.exe)**
```bat
set USE_REAL_BEDROCK=true
set AWS_REGION=us-east-1
set AWS_ACCESS_KEY_ID=your-key-id
set AWS_SECRET_ACCESS_KEY=your-secret
set AWS_SESSION_TOKEN=your-session-token
set BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-5-5-20251101-v1:0

python -m uvicorn services.engine.main:app --port 8000
```

> Tip: to make the variables permanent across sessions, use `setx USE_REAL_BEDROCK true`
> (etc.) — but `setx` only affects **new** terminals, not the current one. For secrets,
> prefer setting them per-session or via a private `.env` (already git-ignored).

**Before the demo, confirm the AWS side is ready:**
- Model access must be enabled for Claude in **Bedrock → Model access** (`us-east-1`).
- List the inference profiles actually available to you and pick a valid `BEDROCK_MODEL_ID`:
  ```powershell
  aws bedrock list-inference-profiles --region us-east-1 --query "inferenceProfileSummaries[?contains(inferenceProfileId,'sonnet')].inferenceProfileId"
  ```

> Notes:
> - Outbound Bedrock calls need network + AWS credentials, so only use `USE_REAL_BEDROCK=true`
>   on a machine that has both. In stub mode (the default) nothing is required and no network is used.
> - If a real call fails (bad creds, model not enabled, wrong ID), the engine logs the error and
>   automatically falls back to the stub, so the demo never crashes — the verdict will show
>   `model: stub (bedrock error: ...)`.

## Demo flow

1. In the user service, pick **Alice (Finance)** and click **"Access finance DB — 02:10"**.
   Her agenda has a *Q3 audit, 01:00–04:00* → engine clears it as **NORMAL (context-justified)**.
2. Pick **Dan (Engineering)** and click the **"Exfiltrate customer database"** (the wrong action).
   No agenda justification, off-baseline → engine raises a **HIGH severity ANOMALY** that lights
   up red on the admin console in real time.

See `docs/` for the full scenario script.
