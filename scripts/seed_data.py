"""Generate the synthetic company's 2-week behavioural baseline into the SQLite store.

This back-fills the dashboard with historical 'normal' assessed events so the engine's
baseline feels real and the admin console isn't empty on first launch. Run once:

    python -m scripts.seed_data
"""
from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta

from data import company
from services.engine.bedrock_client import BedrockClient
from shared.models import LogEvent
from shared.store import Store


def generate_baseline_events(days: int = 14) -> list[LogEvent]:
    events: list[LogEvent] = []
    start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days)
    for emp in company.employees():
        for d in range(days):
            day = start + timedelta(days=d)
            if day.weekday() >= 5 and emp.employee_id != "emp-raj":
                continue  # most people don't work weekends; Raj is on-call
            # a handful of normal actions per working day
            for _ in range(random.randint(2, 5)):
                hour = random.randint(9, 17)
                resource = random.choice(emp.usual_resources)
                events.append(
                    LogEvent(
                        event_id=f"seed-{uuid.uuid4().hex[:12]}",
                        employee_id=emp.employee_id,
                        timestamp=day + timedelta(hours=hour, minutes=random.randint(0, 59)),
                        action="db_access",
                        resource=resource,
                        source_ip="10.0.%d.%d" % (random.randint(1, 9), random.randint(2, 60)),
                        bytes_out=random.randint(20_000, 2_000_000),
                        details="baseline activity",
                    )
                )
    return events


def main() -> None:
    store = Store()
    # Always use the stub for seeding: the baseline is just historical filler, so we
    # never want to make (slow, paid) real Bedrock calls or require AWS creds here,
    # even if USE_REAL_BEDROCK=true is set in this shell.
    client = BedrockClient(force_stub=True)
    events = generate_baseline_events()
    print(f"Seeding {len(events)} baseline events for {len(company.employees())} employees...")
    for ev in events:
        emp = company.by_id(ev.employee_id)
        assessment = client.assess(emp, ev)
        store.save(ev, assessment)
    stats = store.stats()
    print(f"Done. Store now holds {stats['total']} events "
          f"({stats['alerts']} alerts). Breakdown: {stats['by_verdict']}")


if __name__ == "__main__":
    main()
