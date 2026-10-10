"""Bedrock Claude client.

Two modes:
  * stub (default): deterministic, realistic verdicts with no AWS creds or network.
  * real: calls Claude on Bedrock via boto3 when USE_REAL_BEDROCK=true.

The engine asks the model to behave as a trained NDR anomaly model that has learned a
2-week behavioural baseline AND the employee's professional agenda, then return a strict
JSON verdict.
"""
from __future__ import annotations

import json
import re
from typing import Optional

from shared.config import config
from shared.models import Assessment, Employee, LogEvent

SYSTEM_PROMPT = """You are the detection core of an NDR (Network Detection & Response) \
platform. You have been trained for two weeks on each employee's behavioural baseline AND \
their professional agenda (calendar). Your defining capability is CONTEXT: an action that \
looks anomalous on logs alone may be perfectly legitimate when the employee's agenda \
explains it (e.g. a scheduled overnight audit justifies a 2 a.m. finance-DB login).

Given an employee's baseline, their agenda, and a single new log event, decide whether the \
event is normal, suspicious, or an anomaly. Weigh the agenda heavily: use it to CLEAR events \
that would otherwise look bad, and to RAISE confidence when an action has no justification \
and departs from the baseline.

Critical rule: an agenda entry justifies CONTEXT (accessing a resource at an unusual time), \
but it NEVER justifies bulk data exfiltration to an external host. If you see a large export \
(tens of MB or more) going to an external/public IP, treat it as a high-severity anomaly even \
if a scheduled activity would otherwise explain the access, and say so in your reasoning.

Respond with ONLY a JSON object, no prose, with exactly these keys:
{
  "verdict": "normal" | "suspicious" | "anomaly",
  "severity": "info" | "low" | "medium" | "high" | "critical",
  "confidence": <float 0..1>,
  "agenda_justified": <bool>,
  "agenda_reference": <string or null>,
  "reasoning": <string, 1-3 sentences explaining the decision, citing baseline/agenda>,
  "recommended_action": <string>
}"""


def _build_user_prompt(employee: Employee, event: LogEvent) -> str:
    agenda_lines = (
        "\n".join(
            f"  - {a.start.isoformat()} to {a.end.isoformat()}: {a.title} — {a.description}"
            for a in employee.agenda
        )
        or "  (no agenda entries)"
    )
    return f"""EMPLOYEE
  id: {employee.employee_id}
  name: {employee.name}
  role: {employee.role} ({employee.department})
  typical working hours: {employee.typical_hours}
  usual resources: {", ".join(employee.usual_resources) or "n/a"}

2-WEEK BEHAVIOURAL BASELINE
  {employee.baseline_summary}

PROFESSIONAL AGENDA
{agenda_lines}

NEW LOG EVENT TO ASSESS
  timestamp: {event.timestamp.isoformat()}
  action: {event.action}
  resource: {event.resource}
  source_ip: {event.source_ip}
  bytes_out: {event.bytes_out}
  details: {event.details}

Assess this event. Return ONLY the JSON object."""


def _extract_json(text: str) -> dict:
    """Pull the first JSON object out of a model response."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object in model response: {text[:200]!r}")
    return json.loads(match.group(0))


class BedrockClient:
    def __init__(self, force_stub: bool = False) -> None:
        """force_stub=True keeps the client in stub mode regardless of USE_REAL_BEDROCK.

        Used by the data seeder: generating the baseline must never hit real Bedrock
        (slow, costly, and would require AWS creds just to seed local demo data).
        """
        self.model_id = config.BEDROCK_MODEL_ID
        self._runtime = None
        self._force_stub = force_stub
        if config.USE_REAL_BEDROCK and not force_stub:
            self._init_real()

    # --- real mode ---------------------------------------------------------
    def _init_real(self) -> None:
        import boto3  # imported lazily so stub mode needs no boto3/network

        self._runtime = boto3.client("bedrock-runtime", region_name=config.AWS_REGION)
        resolved = self._resolve_inference_profile()
        if resolved:
            self.model_id = resolved

    def _resolve_inference_profile(self) -> Optional[str]:
        """Pick a Claude Sonnet inference profile that exists in this account/region.

        Falls back to the configured BEDROCK_MODEL_ID if discovery fails.
        """
        try:
            import boto3

            bedrock = boto3.client("bedrock", region_name=config.AWS_REGION)
            profiles = bedrock.list_inference_profiles().get("inferenceProfileSummaries", [])
            # Prefer the exact configured id, else first Claude Sonnet profile.
            ids = [p.get("inferenceProfileId", "") for p in profiles]
            if config.BEDROCK_MODEL_ID in ids:
                return config.BEDROCK_MODEL_ID
            for pid in ids:
                if "anthropic.claude" in pid and "sonnet" in pid:
                    return pid
        except Exception as exc:  # noqa: BLE001 - discovery is best-effort
            print(f"[bedrock] inference-profile discovery failed, using configured id: {exc}")
        return None

    def _invoke_real(self, employee: Employee, event: LogEvent) -> dict:
        # Note: `temperature` is deprecated / rejected by newer Claude models on Bedrock
        # (e.g. Sonnet 5), which raise a ValidationException. We omit it and rely on the
        # model default, which is fine for deterministic, low-variance verdicts.
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 600,
            "system": SYSTEM_PROMPT,
            "messages": [
                {"role": "user", "content": _build_user_prompt(employee, event)}
            ],
        }
        resp = self._runtime.invoke_model(
            modelId=self.model_id,
            body=json.dumps(body),
        )
        payload = json.loads(resp["body"].read())
        text = payload["content"][0]["text"]
        return _extract_json(text)

    # --- stub mode ---------------------------------------------------------
    def _invoke_stub(self, employee: Employee, event: LogEvent) -> dict:
        """Heuristic that mimics an agenda-aware model, for credential-free demos."""
        hour = event.timestamp.hour
        off_hours = hour < 7 or hour >= 20
        unusual_resource = event.resource not in employee.usual_resources
        large_export = event.bytes_out > 50_000_000  # >50 MB
        external_ip = not event.source_ip.startswith(("10.", "192.168.", "172."))

        # Does the agenda justify this event?
        justifying = None
        for a in employee.agenda:
            if a.start <= event.timestamp <= a.end:
                text = f"{a.title} {a.description}".lower()
                if event.resource.split("-")[0] in text or event.action in text:
                    justifying = a
                    break
        # A scheduled agenda entry justifies CONTEXT (accessing a resource at an odd
        # time), but it can never justify bulk exfiltration to an external host. Treat
        # large-export-to-external-IP as a hard signal that overrides any justification.
        hard_exfiltration = large_export and external_ip
        agenda_justified = (justifying is not None) and not hard_exfiltration

        risk = 0
        risk += 2 if off_hours else 0
        risk += 2 if unusual_resource else 0
        risk += 3 if large_export else 0
        risk += 3 if external_ip else 0
        if agenda_justified:
            risk -= 4  # the agenda clears apparent risk (context only)

        if risk <= 1:
            verdict, severity, conf = "normal", "info", 0.9
        elif risk <= 4:
            verdict, severity, conf = "suspicious", "low", 0.6
        elif risk <= 6:
            verdict, severity, conf = "anomaly", "medium", 0.75
        else:
            verdict, severity, conf = "anomaly", "high", 0.9
        if hard_exfiltration:
            verdict, severity, conf = "anomaly", "critical", 0.96

        if agenda_justified:
            reasoning = (
                f"Event at {event.timestamp:%H:%M} would look off-baseline, but the agenda "
                f"entry '{justifying.title}' ({justifying.start:%H:%M}-{justifying.end:%H:%M}) "
                f"explains access to {event.resource}. Context-justified."
            )
            recommended = "No action — behaviour matches a scheduled, authorised activity."
        elif verdict == "normal":
            reasoning = "Action is within working hours and matches the behavioural baseline."
            recommended = "No action."
        else:
            flags = []
            if off_hours:
                flags.append("off-hours")
            if unusual_resource:
                flags.append(f"never accesses {event.resource}")
            if large_export:
                flags.append(f"{event.bytes_out/1e6:.0f} MB exfiltrated")
            if external_ip:
                flags.append(f"external IP {event.source_ip}")
            if hard_exfiltration and justifying is not None:
                prefix = (
                    f"The agenda entry '{justifying.title}' authorises access, but NOT a bulk "
                    f"export to an external host. Overriding the justification. "
                )
            else:
                prefix = "No agenda entry justifies this. "
            reasoning = prefix + "Departs from baseline: " + "; ".join(flags) + "."
            recommended = (
                "Isolate the endpoint and open an incident; verify with the employee."
                if severity in {"high", "critical"}
                else "Flag for analyst review."
            )

        return {
            "verdict": verdict,
            "severity": severity,
            "confidence": conf,
            "agenda_justified": agenda_justified,
            "agenda_reference": (justifying.title if justifying else None),
            "reasoning": reasoning,
            "recommended_action": recommended,
        }

    # --- public API --------------------------------------------------------
    def assess(self, employee: Employee, event: LogEvent) -> Assessment:
        if config.USE_REAL_BEDROCK and not self._force_stub and self._runtime is not None:
            try:
                raw = self._invoke_real(employee, event)
                model_used = f"bedrock:{self.model_id}"
            except Exception as exc:  # noqa: BLE001 - fall back so demo never dies
                print(f"[bedrock] real call failed, falling back to stub: {exc}")
                raw = self._invoke_stub(employee, event)
                model_used = f"stub (bedrock error: {type(exc).__name__})"
        else:
            raw = self._invoke_stub(employee, event)
            model_used = "stub"

        return Assessment(
            event_id=event.event_id,
            employee_id=event.employee_id,
            timestamp=event.timestamp,
            verdict=raw["verdict"],
            severity=raw["severity"],
            confidence=float(raw["confidence"]),
            agenda_justified=bool(raw.get("agenda_justified", False)),
            agenda_reference=raw.get("agenda_reference"),
            reasoning=raw.get("reasoning", ""),
            recommended_action=raw.get("recommended_action", ""),
            model_used=model_used,
        )
