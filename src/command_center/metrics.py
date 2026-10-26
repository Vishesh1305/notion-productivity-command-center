"""Refresh the current week's raw Top 3 follow-through count."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from .notion import AmbiguousWrite, NotionClient, prop_select, prop_text, rich_text
from .operations import find_log
from .rules import period_key, top3_follow_through, week_start


def _task(row: dict) -> dict:
    raw_stamp = (row.get("properties", {}).get("Completed at", {}).get("date") or {}).get("start")
    stamp = datetime.fromisoformat(raw_stamp.replace("Z", "+00:00")) if raw_stamp else None
    return {"status": prop_select(row, "Status"), "completed_at": stamp}


def _daily(row: dict) -> dict:
    props = row.get("properties", {})
    slots = []
    for index in range(1, 4):
        relation = props.get(f"Confirmed Top {index}", {}).get("relation") or []
        if len(relation) > 1:
            raise ValueError(f"Daily Log {row['id']} has multiple Tasks in Top {index}")
        if relation:
            slots.append(relation[0]["id"])
    return {
        "state": prop_select(row, "State"),
        "period_key": prop_text(row, "Period key"),
        "confirmed_top": slots,
    }


def refresh_week_metric(client: NotionClient, task_source: str, log_source: str,
                        day: date) -> dict | None:
    """Write a weekly snapshot; no Weekly Log is created by a passive refresh."""
    weekly = find_log(client, log_source, "Weekly", period_key("Weekly", day))
    if not weekly:
        return None
    start = week_start(day)
    end = start + timedelta(days=6)
    logs = []
    seen_days: set[str] = set()
    for row in client.query_all(log_source):
        if prop_select(row, "Period type") != "Daily":
            continue
        key = prop_text(row, "Period key")
        if start.isoformat() <= key <= end.isoformat():
            if key in seen_days:
                raise ValueError(f"Duplicate Daily Planning Log: {key}")
            seen_days.add(key)
            logs.append(_daily(row))
    task_ids = {task_id for log in logs for task_id in log["confirmed_top"]}
    tasks = {row["id"]: _task(row) for row in client.query_all(task_source)
             if row["id"] in task_ids}
    result = top3_follow_through(logs, tasks, day)
    warning = "; ".join(result["attention"])
    if len(warning) > 1900:
        raise ValueError("Metric needs attention text exceeded safe Notion length")
    props = weekly.get("properties", {})
    current = (
        props.get("Completed on planned day", {}).get("number"),
        props.get("Confirmed slots", {}).get("number"),
        prop_text(weekly, "Metric needs attention"),
    )
    desired = (result["completed"], result["confirmed"], warning)
    if current == desired:
        return {"page": weekly, **result, "changed": False}
    changes = {
        "Completed on planned day": {"number": result["completed"]},
        "Confirmed slots": {"number": result["confirmed"]},
        "Metric needs attention": {"rich_text": rich_text(warning)},
    }
    try:
        updated = client.request("PATCH", f"/pages/{weekly['id']}", {"properties": changes})
    except AmbiguousWrite:
        updated = client.request("GET", f"/pages/{weekly['id']}")
        actual = updated.get("properties", {})
        if (actual.get("Completed on planned day", {}).get("number"),
            actual.get("Confirmed slots", {}).get("number"),
            prop_text(updated, "Metric needs attention")) != desired:
            raise
    return {"page": updated, **result, "changed": True}
