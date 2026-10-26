"""Explicit record operations for manual and coding-client use."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from .notion import AmbiguousWrite, NotionClient, prop_select, prop_text, rich_text
from .rules import last_day_of_month, period_key, week_start


def ensure_source(page: dict, source_id: str) -> None:
    parent = page.get("parent", {})
    if parent.get("data_source_id") != source_id:
        raise ValueError("Page is outside the expected command-center data source")


def block_text(value: str) -> list[dict]:
    return [{"object": "block", "type": "paragraph",
             "paragraph": {"rich_text": rich_text(value[i:i + 1900])}}
            for i in range(0, len(value), 1900)]


def quick_add(client: NotionClient, source_id: str, raw: str) -> dict:
    if not raw.strip():
        raise ValueError("Capture text is empty")
    if len(raw) > 40_000:
        raise ValueError("Capture exceeds 40,000 characters")
    name = raw.strip().replace("\n", " ")[:90]
    payload = {"parent": {"type": "data_source_id", "data_source_id": source_id},
               "properties": {"Name": {"title": rich_text(name)},
                              "Status": {"status": {"name": "New"}}},
               "children": block_text(raw)}
    # Captures intentionally have no dedupe key. On an ambiguous POST, surface
    # the failure instead of guessing that another identical capture is ours.
    return client.request("POST", "/pages", payload)


def complete_task(client: NotionClient, source_id: str, task_id: str,
                  when: datetime | None = None) -> dict:
    page = client.request("GET", f"/pages/{task_id}")
    ensure_source(page, source_id)
    current = prop_select(page, "Status")
    if current == "Cancelled":
        raise ValueError("Cancelled Task cannot be silently completed")
    stamp = (page.get("properties", {}).get("Completed at", {}).get("date") or {}).get("start")
    if current == "Done" and stamp:
        return page
    if current == "Done" and not stamp:
        raise ValueError("Done Task is missing Completed at; confirm its actual completion time")
    when = when or datetime.now(timezone.utc)
    props = {"Status": {"status": {"name": "Done"}},
             "Completed at": {"date": {"start": stamp or when.isoformat()}}}
    try:
        return client.request("PATCH", f"/pages/{task_id}", {"properties": props})
    except AmbiguousWrite:
        current_page = client.request("GET", f"/pages/{task_id}")
        if prop_select(current_page, "Status") == "Done" and current_page.get("properties", {}).get("Completed at", {}).get("date"):
            return current_page
        raise


def cancel_task(client: NotionClient, source_id: str, task_id: str,
                reason: str, when: datetime | None = None) -> dict:
    if not reason.strip():
        raise ValueError("Cancellation needs a reason")
    page = client.request("GET", f"/pages/{task_id}")
    ensure_source(page, source_id)
    current = prop_select(page, "Status")
    if current == "Done":
        raise ValueError("Done Task cannot be silently cancelled")
    stamp = (page.get("properties", {}).get("Cancelled at", {}).get("date") or {}).get("start")
    old_reason = prop_text(page, "Cancellation reason")
    if current == "Cancelled":
        if stamp and old_reason == reason:
            return page
        raise ValueError("Cancelled Task needs a reviewed correction")
    when = when or datetime.now(timezone.utc)
    props = {"Status": {"status": {"name": "Cancelled"}},
             "Cancelled at": {"date": {"start": when.isoformat()}},
             "Cancellation reason": {"rich_text": rich_text(reason)}}
    try:
        return client.request("PATCH", f"/pages/{task_id}", {"properties": props})
    except AmbiguousWrite:
        current_page = client.request("GET", f"/pages/{task_id}")
        if prop_select(current_page, "Status") == "Cancelled" and \
                current_page.get("properties", {}).get("Cancelled at", {}).get("date") and \
                prop_text(current_page, "Cancellation reason") == reason:
            return current_page
        raise


def set_waiting(client: NotionClient, source_id: str, task_id: str,
                reason: str) -> dict:
    if not reason.strip():
        raise ValueError("Waiting needs a reason")
    page = client.request("GET", f"/pages/{task_id}")
    ensure_source(page, source_id)
    if prop_select(page, "Status") in ("Done", "Cancelled"):
        raise ValueError("Closed Task needs explicit reopening")
    props = {"Status": {"status": {"name": "Waiting"}},
             "Waiting reason": {"rich_text": rich_text(reason)}}
    try:
        return client.request("PATCH", f"/pages/{task_id}", {"properties": props})
    except AmbiguousWrite:
        current_page = client.request("GET", f"/pages/{task_id}")
        if prop_select(current_page, "Status") == "Waiting" and prop_text(current_page, "Waiting reason") == reason:
            return current_page
        raise


def find_log(client: NotionClient, source_id: str, kind: str, key: str) -> dict | None:
    rows = [row for row in client.query_all(source_id)
            if prop_select(row, "Period type") == kind and prop_text(row, "Period key") == key]
    if len(rows) > 1:
        raise ValueError(f"Duplicate Planning Log: {kind}/{key}")
    return rows[0] if rows else None


def create_log(client: NotionClient, source_id: str, kind: str, key: str,
               start: date, end: date) -> dict:
    existing = find_log(client, source_id, kind, key)
    if existing:
        return existing
    payload = {"parent": {"type": "data_source_id", "data_source_id": source_id},
               "properties": {"Name": {"title": rich_text(f"{kind} {key}")},
                              "Period type": {"select": {"name": kind}},
                              "Period key": {"rich_text": rich_text(key)},
                              "Start": {"date": {"start": start.isoformat()}},
                              "End": {"date": {"start": end.isoformat()}},
                              "State": {"select": {"name": "Draft"}}}}
    try:
        return client.request("POST", "/pages", payload)
    except AmbiguousWrite:
        found = find_log(client, source_id, kind, key)
        if not found:
            raise
        return found


def confirm_day(client: NotionClient, task_source: str, log_source: str,
                day: date, task_ids: list[str], change_note: str = "") -> dict:
    if not 1 <= len(task_ids) <= 3 or len(set(task_ids)) != len(task_ids):
        raise ValueError("Confirm one to three distinct Tasks")
    key = period_key("Daily", day)
    existing = find_log(client, log_source, "Daily", key)
    if existing and prop_select(existing, "State") == "Confirmed":
        existing_ids = [relation[0]["id"] for i in range(1, 4)
                        if (relation := existing.get("properties", {}).get(f"Confirmed Top {i}", {}).get("relation") or [])]
        if existing_ids == task_ids:
            return existing
        if not change_note.strip():
            raise ValueError("Replanning a confirmed day needs a change note")
    for task_id in task_ids:
        page = client.request("GET", f"/pages/{task_id}")
        ensure_source(page, task_source)
        if prop_select(page, "Status") not in ("To do", "In progress") or \
                prop_select(page, "Commitment") != "Committed":
            raise ValueError(f"Task is not open and committed: {task_id}")
    week = week_start(day)
    weekly = create_log(client, log_source, "Weekly", period_key("Weekly", day),
                        week, week + timedelta(days=6))
    daily = existing or create_log(client, log_source, "Daily", key, day, day)
    props = {"State": {"select": {"name": "Confirmed"}},
             "Related week": {"relation": [{"id": weekly["id"]}]},
             "Confirmed at": {"date": {"start": datetime.now(timezone.utc).isoformat()}},
             **{f"Confirmed Top {i}": {"relation": [{"id": task_ids[i - 1]}] if i <= len(task_ids) else []}
                for i in range(1, 4)}}
    if change_note:
        props["Change note"] = {"rich_text": rich_text(change_note)}
    try:
        return client.request("PATCH", f"/pages/{daily['id']}", {"properties": props})
    except AmbiguousWrite:
        current = client.request("GET", f"/pages/{daily['id']}")
        actual = [(current.get("properties", {}).get(f"Confirmed Top {i}", {}).get("relation") or [])
                  for i in range(1, 4)]
        actual_ids = [r[0]["id"] for r in actual if r]
        if prop_select(current, "State") == "Confirmed" and actual_ids == task_ids:
            return current
        raise


def confirm_week(client: NotionClient, log_source: str, day: date,
                 priorities: list[str], change_note: str = "") -> dict:
    if not 1 <= len(priorities) <= 2 or any(not item.strip() for item in priorities):
        raise ValueError("Confirm one or two nonempty weekly priorities")
    if len(set(priorities)) != len(priorities):
        raise ValueError("Weekly priorities must be distinct")
    start = week_start(day)
    weekly = create_log(client, log_source, "Weekly", period_key("Weekly", day),
                        start, start + timedelta(days=6))
    previous = [prop_text(weekly, f"Confirmed priority {i}") for i in range(1, 3)]
    previous = [item for item in previous if item]
    if prop_select(weekly, "State") == "Confirmed":
        if previous == priorities:
            return weekly
        if not change_note.strip():
            raise ValueError("Changing confirmed weekly priorities needs a change note")
    props = {"State": {"select": {"name": "Confirmed"}},
             "Confirmed at": {"date": {"start": datetime.now(timezone.utc).isoformat()}},
             **{f"Confirmed priority {i}": {"rich_text": rich_text(priorities[i - 1] if i <= len(priorities) else "")}
                for i in range(1, 3)}}
    if change_note:
        props["Change note"] = {"rich_text": rich_text(change_note)}
    try:
        return client.request("PATCH", f"/pages/{weekly['id']}", {"properties": props})
    except AmbiguousWrite:
        current = client.request("GET", f"/pages/{weekly['id']}")
        actual = [prop_text(current, f"Confirmed priority {i}") for i in range(1, 3)]
        if prop_select(current, "State") == "Confirmed" and [x for x in actual if x] == priorities:
            return current
        raise


def draft_review(client: NotionClient, log_source: str, kind: str, day: date) -> dict:
    """Create the distinct Sunday or month-end draft without adopting choices."""
    if kind == "Weekly":
        if day.weekday() != 6:
            raise ValueError("Weekly review is for the closing Sunday")
        start = week_start(day)
        end = day
    elif kind == "Monthly":
        if not last_day_of_month(day):
            raise ValueError("Monthly review is for the last calendar day")
        start = day.replace(day=1)
        end = day
    else:
        raise ValueError("Review kind must be Weekly or Monthly")
    return create_log(client, log_source, kind, period_key(kind, day), start, end)
