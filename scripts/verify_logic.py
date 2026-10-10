"""Standalone verification of the stub detection logic against the demo scenarios.

Runs WITHOUT pydantic/fastapi/boto3 (unavailable in some sandboxes). It re-implements
the tiny data-holder shape the stub needs and drives the real heuristic from
bedrock_client via lightweight shims, then asserts the expected verdicts.

Run: python scripts/verify_logic.py
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from types import SimpleNamespace


# --- minimal stand-ins matching the fields the stub reads --------------------
@dataclass
class _Agenda:
    title: str
    start: datetime
    end: datetime
    description: str = ""


@dataclass
class _Emp:
    employee_id: str
    name: str
    role: str
    department: str
    typical_hours: str
    baseline_summary: str
    usual_resources: list = field(default_factory=list)
    agenda: list = field(default_factory=list)


@dataclass
class _Event:
    event_id: str
    employee_id: str
    timestamp: datetime
    action: str
    resource: str
    source_ip: str
    bytes_out: int = 0
    details: str = ""


# --- import ONLY the pure functions from the client (no pydantic needed) -----
# We copy the heuristic by importing the module's source and exec-ing the stub.
# Simpler: re-create the stub call by importing the function logic directly.
import importlib.util
import pathlib

_mod_path = pathlib.Path(__file__).resolve().parent.parent / "services" / "engine" / "bedrock_client.py"
_src = _mod_path.read_text()

# Extract the _invoke_stub body by executing the module in a namespace where the
# heavy imports (shared.*) are stubbed out.
ns: dict = {}
fake_models = SimpleNamespace(Assessment=object, Employee=object, LogEvent=object)
fake_config = SimpleNamespace(
    config=SimpleNamespace(USE_REAL_BEDROCK=False, BEDROCK_MODEL_ID="x", AWS_REGION="us-east-1")
)
sys.modules["shared"] = SimpleNamespace()
sys.modules["shared.models"] = fake_models
sys.modules["shared.config"] = fake_config
exec(compile(_src, str(_mod_path), "exec"), ns)

BedrockClient = ns["BedrockClient"]
client = BedrockClient()  # stub mode (USE_REAL_BEDROCK False)


def assess(emp, ev):
    return client._invoke_stub(emp, ev)


TODAY = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)


def t(h, m=0):
    return TODAY + timedelta(hours=h, minutes=m)


# --- scenarios ---------------------------------------------------------------
alice = _Emp(
    "emp-alice", "Alice", "Analyst", "Finance", "08:30-18:00",
    "office hours only", ["finance-db", "erp", "mail"],
    [_Agenda("Q3 financial close audit", t(1), t(4), "Overnight audit of finance-db")],
)
dan = _Emp(
    "emp-dan", "Dan", "Engineer", "Engineering", "09:30-19:00",
    "small code pulls only", ["code-repo", "ci", "staging-db"],
    [_Agenda("Deploy window", t(15), t(16), "staging deploy")],
)

cases = [
    # (name, emp, event, expected_verdict, expect_agenda_justified)
    ("Alice ERP normal", alice,
     _Event("1", "emp-alice", t(10, 15), "db_access", "erp", "10.0.4.21", 120_000),
     "normal", False),
    ("Alice 2am audit (context-cleared)", alice,
     _Event("2", "emp-alice", t(2, 10), "db_access", "finance-db", "10.0.4.21", 2_400_000),
     "normal", True),
    ("Alice exfiltration (CRITICAL)", alice,
     _Event("3", "emp-alice", t(2, 40), "data_export", "finance-db", "203.0.113.44", 180_000_000),
     "anomaly", False),
    ("Dan customer-db exfiltration (the wrong action)", dan,
     _Event("4", "emp-dan", t(21, 50), "data_export", "customer-db", "198.51.100.9", 240_000_000),
     "anomaly", False),
    ("Dan normal deploy", dan,
     _Event("5", "emp-dan", t(15, 20), "deploy", "ci", "10.0.7.12", 500_000),
     "normal", True),
]

failures = 0
print("Scenario verification (stub logic):\n")
for name, emp, ev, exp_verdict, exp_agenda in cases:
    r = assess(emp, ev)
    ok_v = r["verdict"] == exp_verdict
    ok_a = r["agenda_justified"] == exp_agenda
    status = "PASS" if (ok_v and ok_a) else "FAIL"
    if status == "FAIL":
        failures += 1
    print(f"[{status}] {name}")
    print(f"        verdict={r['verdict']} severity={r['severity']} "
          f"agenda_justified={r['agenda_justified']} conf={r['confidence']}")
    print(f"        reason: {r['reasoning']}")
    if not ok_v:
        print(f"        !! expected verdict {exp_verdict!r}")
    if not ok_a:
        print(f"        !! expected agenda_justified {exp_agenda}")
    print()

if failures:
    print(f"{failures} scenario(s) FAILED")
    sys.exit(1)
print("All scenarios passed ✅")
