"""Local generator for explicitly managed recurrence series."""

from __future__ import annotations

import json
from datetime import date, timedelta

from .notion import AmbiguousWrite, NotionClient, prop_select, prop_text, rich_text


def occurrence_dates(rule: dict, today: date, *, horizon_days: int = 14) -> list[date]:
    """Generate forward only; never backfill missed dates after Mac downtime."""
    if not 1 <= horizon_days <= 14:
        raise ValueError("Horizon must be 1..14 days")
    frequency = rule.get("frequency")
    interval = rule.get("interval", 1)
    anchor = date.fromisoformat(rule["anchor"])
    if not isinstance(interval, int) or not 1 <= interval <= 365:
        raise ValueError("Invalid interval")
    weekdays = rule.get("weekdays", [])
    if frequency == "weekly" and (not weekdays or any(not isinstance(x, int) or x not in range(7) for x in weekdays)):
        raise ValueError("Weekly rule needs weekdays 0..6")
    if frequency not in ("daily", "weekly"):
        raise ValueError("Only daily and weekly managed rules are supported")
    until = date.fromisoformat(rule["until"]) if rule.get("until") else None
    result = []
    for offset in range(horizon_days + 1):
        day = today + timedelta(days=offset)
        if day < anchor or (until and day > until):
            continue
        if frequency == "daily" and (day - anchor).days % interval == 0:
            result.append(day)
        if frequency == "weekly" and day.weekday() in weekdays and \
                ((day - timedelta(days=day.weekday())) -
                 (anchor - timedelta(days=anchor.weekday()))).days // 7 % interval == 0:
            result.append(day)
    return result


def occurrence_key(series_key: str, day: date) -> str:
    if not series_key.strip():
        raise ValueError("Series key required")
    return f"{series_key}:{day.isoformat()}"


def generate(client: NotionClient, source_id: str, today: date) -> list[str]:
    rows = client.query_all(source_id)
    series = [r for r in rows if prop_select(r, "Record type") == "Series" and
              prop_select(r, "Generation mode") == "Managed local generator"]
    existing = {prop_text(r, "Occurrence key") for r in rows if prop_text(r, "Occurrence key")}
    created = []
    for item in series:
        series_key = prop_text(item, "Series key")
        rule = json.loads(prop_text(item, "Recurrence rule"))
        title = prop_text(item, "Name")
        for day in occurrence_dates(rule, today):
            key = occurrence_key(series_key, day)
            if key in existing:
                continue
            payload = {"parent": {"type": "data_source_id", "data_source_id": source_id},
                       "properties": {
                           "Name": {"title": rich_text(title)},
                           "Record type": {"select": {"name": "Task"}},
                           "Status": {"status": {"name": "To do"}},
                           "Commitment": {"select": {"name": "Committed"}},
                           "Priority": {"select": {"name": "Normal"}},
                           "Series": {"relation": [{"id": item["id"]}]},
                           "Series key": {"rich_text": rich_text(series_key)},
                           "Occurrence date": {"date": {"start": day.isoformat()}},
                           "Plan date": {"date": {"start": day.isoformat()}},
                           "Occurrence key": {"rich_text": rich_text(key)},
                       }}
            try:
                page = client.request("POST", "/pages", payload)
            except AmbiguousWrite:
                matches = [r for r in client.query_all(source_id) if prop_text(r, "Occurrence key") == key]
                if len(matches) != 1:
                    raise
                page = matches[0]
            existing.add(key)
            created.append(page["id"])
    return created
