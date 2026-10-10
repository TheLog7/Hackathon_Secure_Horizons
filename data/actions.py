"""Predefined clickable actions for each employee in the user service.

Each action is a template the user service turns into a LogEvent at click time.
`kind` drives the UI colour: "normal", "context" (looks bad, agenda clears it),
or "malicious" (the wrong action that should alert).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ActionKind = Literal["normal", "context", "malicious"]


@dataclass
class ActionTemplate:
    key: str
    label: str
    kind: ActionKind
    action: str
    resource: str
    hour: int
    minute: int
    bytes_out: int
    source_ip: str
    details: str


ACTIONS: dict[str, list[ActionTemplate]] = {
    "emp-alice": [
        ActionTemplate("alice-normal", "Open ERP budget sheet — 10:15", "normal",
                       "db_access", "erp", 10, 15, 120_000, "10.0.4.21",
                       "Routine ERP access during working hours."),
        ActionTemplate("alice-audit", "Access finance DB — 02:10", "context",
                       "db_access", "finance-db", 2, 10, 2_400_000, "10.0.4.21",
                       "Finance-DB access in the middle of the night."),
        ActionTemplate("alice-bad", "Export finance DB to external host — 02:40", "malicious",
                       "data_export", "finance-db", 2, 40, 180_000_000, "203.0.113.44",
                       "180 MB export of finance-db to an external IP."),
    ],
    "emp-dan": [
        ActionTemplate("dan-normal", "Pull code repo — 11:00", "normal",
                       "repo_pull", "code-repo", 11, 0, 8_000_000, "10.0.7.12",
                       "Normal code pull."),
        ActionTemplate("dan-deploy", "Trigger staging deploy — 15:20", "context",
                       "deploy", "ci", 15, 20, 500_000, "10.0.7.12",
                       "Staging deploy during the scheduled deploy window."),
        ActionTemplate("dan-bad", "Exfiltrate customer database — 21:50", "malicious",
                       "data_export", "customer-db", 21, 50, 240_000_000, "198.51.100.9",
                       "240 MB dump of customer-db to an external IP, off-hours."),
    ],
    "emp-sara": [
        ActionTemplate("sara-normal", "Open HR records — 09:30", "normal",
                       "db_access", "hr-db", 9, 30, 90_000, "10.0.9.5",
                       "Routine HR access."),
        ActionTemplate("sara-payroll", "Run payroll export — 10:30", "context",
                       "data_export", "hr-db", 10, 30, 3_000_000, "10.0.9.5",
                       "Payroll export during the scheduled payroll window."),
        ActionTemplate("sara-bad", "Download all employee PII — 23:15", "malicious",
                       "data_export", "hr-db", 23, 15, 95_000_000, "192.0.2.77",
                       "95 MB bulk PII export late at night to an external IP."),
    ],
    "emp-raj": [
        ActionTemplate("raj-patch", "Server patch + reboot — 02:30", "context",
                       "maintenance", "servers", 2, 30, 1_000_000, "10.0.1.2",
                       "Night maintenance during the scheduled patch window."),
        ActionTemplate("raj-normal", "Check monitoring dashboard — 14:00", "normal",
                       "db_access", "monitoring", 14, 0, 50_000, "10.0.1.2",
                       "Routine monitoring check."),
        ActionTemplate("raj-bad", "Create hidden admin account — 03:10", "malicious",
                       "privilege_change", "servers", 3, 10, 20_000, "10.0.1.2",
                       "New privileged account outside any change window; no ticket."),
    ],
    "emp-mia": [
        ActionTemplate("mia-crm", "Update CRM from Berlin — 11:00", "context",
                       "db_access", "crm", 11, 0, 400_000, "81.200.0.15",
                       "CRM access from an external IP during the client visit."),
        ActionTemplate("mia-normal", "Send proposal email — 16:00", "normal",
                       "mail_send", "mail", 16, 0, 300_000, "81.200.0.15",
                       "Routine email during travel."),
        ActionTemplate("mia-bad", "Bulk-export entire CRM — 16:30", "malicious",
                       "data_export", "crm", 16, 30, 160_000_000, "45.33.12.1",
                       "160 MB full CRM export to an unknown external host."),
    ],
    "emp-tom": [
        ActionTemplate("tom-cms", "Publish campaign page — 14:10", "context",
                       "publish", "cms", 14, 10, 600_000, "10.0.6.30",
                       "CMS publish during the campaign review."),
        ActionTemplate("tom-normal", "View analytics — 10:00", "normal",
                       "db_access", "analytics", 10, 0, 40_000, "10.0.6.30",
                       "Routine analytics view."),
        ActionTemplate("tom-bad", "Access finance DB — 18:30", "malicious",
                       "db_access", "finance-db", 18, 30, 500_000, "10.0.6.30",
                       "Marketing accessing finance-db — never seen in baseline."),
    ],
}


def for_employee(employee_id: str) -> list[ActionTemplate]:
    return ACTIONS.get(employee_id, [])
