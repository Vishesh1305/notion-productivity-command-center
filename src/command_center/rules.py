"""Pure domain calculations used by validation and sync jobs."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from math import ceil
from zoneinfo import ZoneInfo

from .definitions import TIMEZONE

ZONE = ZoneInfo(TIMEZONE)


def local_date(value: datetime) -> date:
    if value.tzinfo is None:
        raise ValueError("A timestamp needs an explicit timezone")
    return value.astimezone(ZONE).date()


def week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


def period_key(kind: str, day: date) -> str:
    if kind == "Daily":
        return day.isoformat()
    if kind == "Weekly":
        return week_start(day).isoformat()
    if kind == "Monthly":
        return day.strftime("%Y-%m")
    raise ValueError(kind)


def last_day_of_month(day: date) -> bool:
    return (day + timedelta(days=1)).month != day.month


def phase_readiness(tasks: list[dict]) -> dict:
    blocking = [t for t in tasks if not t.get("non_blocking_for_phase", False)]
    done = sum(t.get("status") == "Done" for t in blocking)
    return {"blocking": len(blocking), "done": done,
            "remaining": len(blocking) - done,
            "ready_for_review": bool(blocking) and done == len(blocking)}


def top3_follow_through(logs: list[dict], tasks: dict[str, dict], day: date) -> dict:
    """Count current-week final confirmed slots completed on their planned local day."""
    start = week_start(day)
    end = start + timedelta(days=6)
    numerator = denominator = 0
    attention: list[str] = []
    for log in logs:
        if log.get("state") != "Confirmed":
            continue
        log_day = date.fromisoformat(log["period_key"])
        if not start <= log_day <= end:
            continue
        slots = [x for x in log.get("confirmed_top", []) if x]
        if len(slots) > 3 or len(slots) != len(set(slots)):
            attention.append(f"Invalid Top 3 for {log_day}")
            continue
        denominator += len(slots)
        for task_id in slots:
            task = tasks.get(task_id)
            if not task:
                attention.append(f"Missing Task {task_id}")
                continue
            stamp = task.get("completed_at")
            if task.get("status") == "Done" and not stamp:
                attention.append(f"Done without Completed at: {task_id}")
                continue
            if stamp and local_date(stamp) == log_day and task.get("status") == "Done":
                numerator += 1
    return {"completed": numerator, "confirmed": denominator, "attention": attention}


@dataclass(frozen=True)
class HabitDefinition:
    cadence: str
    start: date
    end: date | None = None
    weekdays: frozenset[int] = frozenset()
    weekly_target: int | None = None


def habit_consistency(
    definition: HabitDefinition,
    start: date,
    end: date,
    checkins: list[dict],
    pauses: list[tuple[date, date]],
) -> dict:
    """Inclusive range; paused dates and excused opportunities leave denominator."""
    if end < start:
        raise ValueError("End precedes start")
    if definition.cadence == "N per week" and (not definition.weekly_target or not 1 <= definition.weekly_target <= 7):
        raise ValueError("Weekly target must be 1..7")
    by_day: dict[date, set[str]] = {}
    for row in checkins:
        d = row["date"]
        if start <= d <= end:
            by_day.setdefault(d, set()).add(row["status"])
    eligible = completed = 0
    cursor = week_start(start)
    while cursor <= end:
        week_days = [cursor + timedelta(days=i) for i in range(7)]
        active = [d for d in week_days if start <= d <= end and d >= definition.start
                  and (definition.end is None or d <= definition.end)
                  and not any(a <= d <= b for a, b in pauses)]
        if definition.cadence == "Daily":
            opportunity = active
            excused = sum("Excused" in by_day.get(d, ()) for d in opportunity)
            target = len(opportunity) - excused
            done = sum("Done" in by_day.get(d, ()) and "Excused" not in by_day.get(d, ()) for d in opportunity)
        elif definition.cadence == "Selected weekdays":
            opportunity = [d for d in active if d.weekday() in definition.weekdays]
            excused = sum("Excused" in by_day.get(d, ()) for d in opportunity)
            target = len(opportunity) - excused
            done = sum("Done" in by_day.get(d, ()) and "Excused" not in by_day.get(d, ()) for d in opportunity)
        elif definition.cadence == "N per week":
            target = ceil(definition.weekly_target * len(active) / 7)
            target = max(0, target - sum("Excused" in by_day.get(d, ()) for d in active))
            done = sum("Done" in by_day.get(d, ()) and "Excused" not in by_day.get(d, ()) for d in active)
        else:
            raise ValueError(definition.cadence)
        eligible += target
        completed += min(done, target)
        cursor += timedelta(days=7)
    return {"done": completed, "eligible": eligible}


def duplicate_keys(rows: list[dict], field: str) -> list[str]:
    counts = Counter(row.get(field) for row in rows if row.get(field))
    return sorted(key for key, count in counts.items() if count > 1)


def validate_task(task: dict) -> list[str]:
    errors = []
    if not task.get("name", "").strip():
        errors.append("Task has no name")
    if task.get("status") == "Waiting" and not task.get("waiting_reason", "").strip():
        errors.append("Waiting needs a reason")
    if task.get("status") == "Done" and not task.get("completed_at"):
        errors.append("Done needs Completed at")
    if task.get("status") == "Cancelled" and not task.get("cancelled_at"):
        errors.append("Cancelled needs Cancelled at")
    if task.get("project") and task.get("standalone_area"):
        errors.append("Project Task has a conflicting Standalone Area")
    return errors
