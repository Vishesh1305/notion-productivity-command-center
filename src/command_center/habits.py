"""Habit check-ins and reports over the existing versioned definition."""

from __future__ import annotations

from datetime import date, datetime, timezone

from .notion import AmbiguousWrite, NotionClient, prop_select, prop_text, rich_text
from .operations import ensure_source
from .rules import HabitDefinition, habit_consistency, local_date

WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def _habit_definition(page: dict) -> HabitDefinition:
    props = page["properties"]
    start = (props.get("Start date", {}).get("date") or {}).get("start")
    if not start:
        raise ValueError("Habit needs a Start date before check-ins or reports")
    end = (props.get("End date", {}).get("date") or {}).get("start")
    weekdays = frozenset(WEEKDAYS.index(value["name"]) for value in
                         props.get("Weekdays", {}).get("multi_select", []))
    return HabitDefinition(
        cadence=prop_select(page, "Cadence type") or "",
        start=date.fromisoformat(start[:10]),
        end=date.fromisoformat(end[:10]) if end else None,
        weekdays=weekdays,
        weekly_target=props.get("Weekly target", {}).get("number"),
    )


def _rows_for_habit(client: NotionClient, source_id: str, habit_id: str) -> list[dict]:
    return [row for row in client.query_all(source_id) if habit_id in
            {item["id"] for item in row.get("properties", {}).get("Habit", {}).get("relation", [])}]


def _checkin_key(habit_id: str, day: date) -> str:
    # Notion's native Button formula emits page.id() without UUID separators.
    return f"{habit_id.replace('-', '')}:{day.isoformat()}"


def _canonical_key(value: str) -> str:
    habit_id, separator, day = value.partition(":")
    return f"{habit_id.replace('-', '')}:{day}" if separator else value


def check_in(client: NotionClient, habit_source: str, checkin_source: str,
             habit_id: str, day: date, status: str = "Done", *,
             amount: float | None = None, note: str = "") -> dict:
    """Create one Done/Excused record for an eligible date, or return an exact retry."""
    if status not in ("Done", "Excused"):
        raise ValueError("Check-in status must be Done or Excused")
    if amount is not None and (amount < 0 or status == "Excused"):
        raise ValueError("Amount must be nonnegative and belongs only to Done")
    habit = client.request("GET", f"/pages/{habit_id}")
    ensure_source(habit, habit_source)
    definition = _habit_definition(habit)
    if prop_select(habit, "Status") != "Active":
        raise ValueError("Only an Active Habit accepts new check-ins")
    if day < definition.start or (definition.end and day > definition.end):
        raise ValueError("Check-in date is outside this Habit version")
    if definition.cadence == "Selected weekdays" and day.weekday() not in definition.weekdays:
        raise ValueError("Check-in date is outside the selected weekdays")
    if definition.cadence not in ("Daily", "Selected weekdays", "N per week"):
        raise ValueError("Habit cadence is incomplete")
    if definition.cadence == "Selected weekdays" and not definition.weekdays:
        raise ValueError("Habit selected weekdays are missing")
    if definition.cadence == "N per week" and (not definition.weekly_target or
                                                not 1 <= definition.weekly_target <= 7):
        raise ValueError("Habit weekly target must be 1..7")
    key = _checkin_key(habit_id, day)

    def existing() -> list[dict]:
        return [row for row in _rows_for_habit(client, checkin_source, habit_id)
                if _canonical_key(prop_text(row, "Occurrence key")) == key]

    def matches(row: dict) -> bool:
        return (prop_select(row, "Event type") == "Check-in" and
                prop_select(row, "Check-in status") == status and
                row.get("properties", {}).get("Amount", {}).get("number") == amount and
                prop_text(row, "Note") == note)

    found = existing()
    if len(found) > 1:
        raise ValueError(f"Duplicate Habit Check-in key: {key}")
    if found:
        row = found[0]
        if matches(row):
            return row
        raise ValueError("Existing check-in differs; review the correction explicitly")

    name = prop_text(habit, "Name") or "Habit"
    props = {
        "Name": {"title": rich_text(f"{name} · {day.isoformat()}")},
        "Habit": {"relation": [{"id": habit_id}]},
        "Event type": {"select": {"name": "Check-in"}},
        "Occurrence date": {"date": {"start": day.isoformat()}},
        "Check-in status": {"select": {"name": status}},
        "Occurrence key": {"rich_text": rich_text(key)},
        "Event time": {"date": {"start": datetime.now(timezone.utc).isoformat()}},
    }
    if amount is not None:
        props["Amount"] = {"number": amount}
    if note:
        props["Note"] = {"rich_text": rich_text(note)}
    try:
        return client.request("POST", "/pages", {
            "parent": {"type": "data_source_id", "data_source_id": checkin_source},
            "properties": props,
        })
    except AmbiguousWrite:
        found = existing()
        if len(found) == 1 and matches(found[0]):
            return found[0]
        raise


def habit_report(client: NotionClient, habit_source: str, checkin_source: str,
                 habit_id: str, start: date, end: date) -> dict:
    """Read-only consistency count with explicit duplicate and pause warnings."""
    habit = client.request("GET", f"/pages/{habit_id}")
    ensure_source(habit, habit_source)
    definition = _habit_definition(habit)
    rows = _rows_for_habit(client, checkin_source, habit_id)
    checkins: list[dict] = []
    keys: dict[str, int] = {}
    pause_events: list[tuple[datetime, str]] = []
    warnings: list[str] = []
    for row in rows:
        kind = prop_select(row, "Event type")
        if kind == "Check-in":
            value = (row["properties"].get("Occurrence date", {}).get("date") or {}).get("start")
            if not value:
                warnings.append(f"Check-in missing Occurrence date: {row['id']}")
                continue
            key = prop_text(row, "Occurrence key")
            if key:
                canonical = _canonical_key(key)
                keys[canonical] = keys.get(canonical, 0) + 1
            checkins.append({"date": date.fromisoformat(value[:10]),
                             "status": prop_select(row, "Check-in status")})
        elif kind in ("Pause started", "Pause ended"):
            value = (row["properties"].get("Event time", {}).get("date") or {}).get("start")
            if not value:
                warnings.append(f"Pause event missing Event time: {row['id']}")
                continue
            stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                warnings.append(f"Pause event lacks timezone: {row['id']}")
                continue
            pause_events.append((stamp, kind))
    duplicates = sorted(key for key, count in keys.items() if count > 1)
    if duplicates:
        warnings.append(f"Duplicate check-in keys: {', '.join(duplicates)}")
    pause_events.sort()
    pauses: list[tuple[date, date]] = []
    opened: date | None = None
    for stamp, kind in pause_events:
        day = local_date(stamp)
        if kind == "Pause started":
            if opened is not None:
                warnings.append(f"Overlapping pause started: {day}")
            else:
                opened = day
        elif opened is None:
            warnings.append(f"Pause ended without start: {day}")
        else:
            pauses.append((opened, day))
            opened = None
    if opened is not None:
        pauses.append((opened, end))
    if prop_select(habit, "Status") == "Paused" and opened is None:
        warnings.append("Habit is Paused but has no open Pause started event")
    counts = habit_consistency(definition, start, end, checkins, pauses)
    return {**counts, "warnings": warnings, "habit_id": habit_id,
            "start": start.isoformat(), "end": end.isoformat()}
