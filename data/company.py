"""The synthetic company: employees, their 2-week baseline, usual resources, and agendas.

Agenda timestamps are built relative to a reference "today" so the demo always has
entries that line up with the clickable actions in the user service.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from shared.models import AgendaEntry, Employee

# Reference day used to anchor agendas. The user service emits events on this same day.
TODAY = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)


def _t(hour: int, minute: int = 0, day_offset: int = 0) -> datetime:
    return TODAY + timedelta(days=day_offset, hours=hour, minutes=minute)


EMPLOYEES: list[Employee] = [
    Employee(
        employee_id="emp-alice",
        name="Alice Moreau",
        role="Senior Financial Analyst",
        department="Finance",
        typical_hours="08:30-18:00",
        baseline_summary=(
            "Works weekdays 08:30-18:00 from the office network (10.0.x). Daily access to "
            "finance-db and the ERP. Never exports more than a few MB. No weekend or "
            "night activity in the last two weeks."
        ),
        usual_resources=["finance-db", "erp", "mail", "intranet"],
        agenda=[
            AgendaEntry(
                title="Q3 financial close audit",
                start=_t(1, 0),
                end=_t(4, 0),
                description="Overnight audit of finance-db with external auditors.",
            ),
            AgendaEntry(
                title="Budget review",
                start=_t(10, 0),
                end=_t(11, 30),
                description="ERP budget review meeting.",
            ),
        ],
    ),
    Employee(
        employee_id="emp-dan",
        name="Dan Weber",
        role="Backend Engineer",
        department="Engineering",
        typical_hours="09:30-19:00",
        baseline_summary=(
            "Works weekdays 09:30-19:00 from 10.0.x. Accesses the code repo, CI, and the "
            "staging DB. Routine data transfers are small (code pulls). Never touches "
            "customer-db and has no history of large external uploads."
        ),
        usual_resources=["code-repo", "ci", "staging-db", "mail", "intranet"],
        agenda=[
            AgendaEntry(
                title="Sprint standup",
                start=_t(9, 30),
                end=_t(9, 45),
                description="Daily engineering standup.",
            ),
            AgendaEntry(
                title="Deploy window",
                start=_t(15, 0),
                end=_t(16, 0),
                description="Staging deploy via CI.",
            ),
        ],
    ),
    Employee(
        employee_id="emp-sara",
        name="Sara Nkemdirim",
        role="HR Business Partner",
        department="Human Resources",
        typical_hours="09:00-17:30",
        baseline_summary=(
            "Works weekdays 09:00-17:30 from 10.0.x. Daily access to hr-db and mail. "
            "Small, routine exports (offer letters). No engineering or finance access."
        ),
        usual_resources=["hr-db", "mail", "intranet", "ats"],
        agenda=[
            AgendaEntry(
                title="Payroll preparation",
                start=_t(9, 0),
                end=_t(12, 0),
                description="Monthly payroll run touching hr-db.",
            ),
        ],
    ),
    Employee(
        employee_id="emp-raj",
        name="Raj Patel",
        role="IT Systems Administrator",
        department="IT",
        typical_hours="on-call / rotating",
        baseline_summary=(
            "On-call rotation; legitimately active at odd hours. Broad access to servers "
            "and infra for maintenance. Baseline includes occasional night maintenance "
            "windows, always announced in the agenda."
        ),
        usual_resources=["infra", "servers", "mail", "intranet", "monitoring"],
        agenda=[
            AgendaEntry(
                title="Patch window",
                start=_t(2, 0),
                end=_t(3, 30),
                description="Scheduled server patching and reboot.",
            ),
        ],
    ),
    Employee(
        employee_id="emp-mia",
        name="Mia Lindqvist",
        role="Sales Executive",
        department="Sales",
        typical_hours="08:00-18:00 (travels often)",
        baseline_summary=(
            "Frequently travels; often connects from external IPs via VPN. Daily access "
            "to the CRM. Travel and client visits are reflected in the agenda, which "
            "explains out-of-office and external-IP activity."
        ),
        usual_resources=["crm", "mail", "intranet"],
        agenda=[
            AgendaEntry(
                title="Client visit — Berlin",
                start=_t(8, 0),
                end=_t(18, 0),
                description="On-site at client; CRM access from external/VPN IP expected.",
            ),
        ],
    ),
    Employee(
        employee_id="emp-tom",
        name="Tom Alvarez",
        role="Marketing Manager",
        department="Marketing",
        typical_hours="09:00-17:00",
        baseline_summary=(
            "Works weekdays 09:00-17:00 from 10.0.x. Uses the CMS, analytics, and mail. "
            "No access to finance, HR, or engineering systems. Low data volumes."
        ),
        usual_resources=["cms", "analytics", "mail", "intranet"],
        agenda=[
            AgendaEntry(
                title="Campaign launch review",
                start=_t(14, 0),
                end=_t(15, 0),
                description="Review analytics for the new campaign.",
            ),
        ],
    ),
]


def employees() -> list[Employee]:
    return EMPLOYEES


def by_id(employee_id: str) -> Employee | None:
    return next((e for e in EMPLOYEES if e.employee_id == employee_id), None)
