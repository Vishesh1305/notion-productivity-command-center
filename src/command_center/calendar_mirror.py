"""Read-only Apple Calendar mirror planning and Notion display-cache writer."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from .definitions import TIMEZONE
from .notion import AmbiguousWrite, NotionClient, prop_text, rich_text
from .rules import ZONE, local_date


@dataclass(frozen=True)
class CalendarEvent:
    key: str
    calendar_key: str
    title: str
    start: str
    end: str
    all_day: bool


def calendar_window(now: datetime) -> tuple[datetime, datetime]:
    """Yesterday through day 14, by Vancouver calendar days, end exclusive."""
    today = local_date(now)
    start = datetime.combine(today - timedelta(days=1), time.min, tzinfo=ZONE)
    end = datetime.combine(today + timedelta(days=15), time.min, tzinfo=ZONE)
    return start.astimezone(timezone.utc), end.astimezone(timezone.utc)


def mirror_plan(existing: list[dict], incoming: list[CalendarEvent], *, complete: bool) -> dict:
    """Only a complete EventKit fetch may inactivate a missing mirror row."""
    if len({event.key for event in incoming}) != len(incoming):
        raise ValueError("Duplicate Apple occurrence key in fetch")
    by_key: dict[str, dict] = {}
    for row in existing:
        key = row["key"]
        if key in by_key:
            raise ValueError(f"Duplicate Notion occurrence key: {key}")
        by_key[key] = row
    incoming_keys = {event.key for event in incoming}
    creates, updates, touches, inactivates = [], [], [], []
    for event in incoming:
        old = by_key.get(event.key)
        if old is None:
            creates.append(event)
        elif (any(old[field] != getattr(event, field) for field in
                  ("title", "all_day", "calendar_key"))
              or not _same_display_date(old["start"], old.get("start_zone"), event.start, event.all_day)
              or not _same_display_date(old["end"], old.get("end_zone"), event.end, event.all_day)
              or old.get("state") != "Current"):
            updates.append((old, event))
        else:
            touches.append(old)
    if complete:
        inactivates = [row for row in existing if row["key"] not in incoming_keys and row.get("state") == "Current"]
    return {"creates": creates, "updates": updates, "touches": touches, "inactivates": inactivates}


def _instant(value: str, named_zone: str | None = None) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        if not named_zone:
            raise ValueError("Timed calendar value has no time zone")
        parsed = parsed.replace(tzinfo=ZoneInfo(named_zone))
    return parsed.astimezone(timezone.utc)


def _notion_date(value: str, all_day: bool) -> dict:
    if all_day:
        return {"start": value}
    local = _instant(value).astimezone(ZONE)
    # Notion normalizes named IANA zones to an explicit offset on save. Write
    # that format directly so the date picker opens at Vancouver local time.
    return {"start": local.isoformat(timespec="milliseconds")}


def _same_display_date(current: str | None, zone: str | None, incoming: str, all_day: bool) -> bool:
    if not current:
        return False
    if all_day:
        return current == incoming
    if _instant(current, zone) != _instant(incoming):
        return False
    if zone == TIMEZONE:
        return True
    if zone is not None:
        return False
    desired = _notion_date(incoming, False)["start"]
    return datetime.fromisoformat(current.replace("Z", "+00:00")).utcoffset() == \
        datetime.fromisoformat(desired).utcoffset()


def event_properties(event: CalendarEvent, now: str) -> dict:
    return {
        "Name": {"title": rich_text(event.title[:2000])},
        "Kind": {"select": {"name": "Event"}},
        "Start": {"date": _notion_date(event.start, event.all_day)},
        "End": {"date": _notion_date(event.end, event.all_day)},
        "All day": {"checkbox": event.all_day},
        "State": {"select": {"name": "Current"}},
        "Source calendar key": {"rich_text": rich_text(event.calendar_key)},
        "Source occurrence key": {"rich_text": rich_text(event.key)},
        "Last seen at": {"date": {"start": now}},
    }


def parse_notion_event(row: dict) -> dict:
    props = row["properties"]
    return {
        "id": row["id"], "key": prop_text(row, "Source occurrence key"),
        "calendar_key": prop_text(row, "Source calendar key"),
        "title": prop_text(row, "Name"),
        "start": (props.get("Start", {}).get("date") or {}).get("start"),
        "start_zone": (props.get("Start", {}).get("date") or {}).get("time_zone"),
        "end": (props.get("End", {}).get("date") or {}).get("start"),
        "end_zone": (props.get("End", {}).get("date") or {}).get("time_zone"),
        "all_day": props.get("All day", {}).get("checkbox", False),
        "state": (props.get("State", {}).get("select") or {}).get("name"),
    }


def apple_export(exporter: Path, selected_ids: list[str], start: datetime, end: datetime) -> list[CalendarEvent]:
    if not selected_ids:
        raise ValueError("Select at least one Apple Calendar before syncing")
    result = subprocess.run(
        [str(exporter), "--events", start.isoformat(), end.isoformat(), *selected_ids],
        capture_output=True, text=True, timeout=90, check=False,
    )
    if result.returncode:
        raise RuntimeError("Apple Calendar read failed; inspect calendar permission and selected IDs")
    data = json.loads(result.stdout)
    if not data.get("complete"):
        raise RuntimeError("Apple Calendar fetch was incomplete")
    return [CalendarEvent(**row) for row in data["events"]]


def sync_calendar(client: NotionClient, source_id: str, events: list[CalendarEvent], *,
                  now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    stamp = now.isoformat()
    rows = client.query_all(source_id)
    health = [r for r in rows if (r.get("properties", {}).get("Kind", {}).get("select") or {}).get("name") == "Sync health"]
    if len(health) > 1:
        raise ValueError("Duplicate calendar sync health records")
    old = [parse_notion_event(r) for r in rows if
           (r.get("properties", {}).get("Kind", {}).get("select") or {}).get("name") == "Event"]
    plan = mirror_plan(old, events, complete=True)
    changed = {"created": [], "updated": [], "seen": [], "inactivated": []}
    for event in plan["creates"]:
        # Re-read logical key after an ambiguous write before any retry.
        try:
            page = client.request("POST", "/pages", {
                "parent": {"type": "data_source_id", "data_source_id": source_id},
                "properties": event_properties(event, stamp),
            })
        except AmbiguousWrite:
            candidates = [x for x in client.query_all(source_id) if prop_text(x, "Source occurrence key") == event.key]
            if len(candidates) != 1:
                raise
            page = candidates[0]
        changed["created"].append(page["id"])
    for old_row, event in plan["updates"]:
        client.request("PATCH", f"/pages/{old_row['id']}", {"properties": event_properties(event, stamp)})
        changed["updated"].append(old_row["id"])
    for row in plan["touches"]:
        client.request("PATCH", f"/pages/{row['id']}",
                       {"properties": {"Last seen at": {"date": {"start": stamp}}}})
        changed["seen"].append(row["id"])
    for row in plan["inactivates"]:
        client.request("PATCH", f"/pages/{row['id']}", {"properties": {"State": {"select": {"name": "Expired"}}}})
        changed["inactivated"].append(row["id"])
    props = {"Name": {"title": rich_text("Calendar sync")},
             "Kind": {"select": {"name": "Sync health"}},
             "Last successful sync": {"date": {"start": stamp}}}
    if health:
        client.request("PATCH", f"/pages/{health[0]['id']}", {"properties": props})
    else:
        try:
            client.request("POST", "/pages", {"parent": {"type": "data_source_id", "data_source_id": source_id}, "properties": props})
        except AmbiguousWrite:
            if len([r for r in client.query_all(source_id) if
                    (r.get("properties", {}).get("Kind", {}).get("select") or {}).get("name") == "Sync health"]) != 1:
                raise
    return changed


def stale(last_success: datetime | None, now: datetime) -> bool:
    return last_success is None or now - last_success > timedelta(minutes=30)
