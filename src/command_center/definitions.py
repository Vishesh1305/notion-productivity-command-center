"""Versioned structural contract. No environment IDs or credentials live here."""

from __future__ import annotations

from dataclasses import dataclass

TIMEZONE = "America/Vancouver"
API_VERSION = "2026-03-11"
AREA_SEEDS = (
    "Tech Career", "Education", "Health", "Finances", "Relationships",
    "Home & Life Admin", "Recreation",
)
PAGES = (
    "Home", "Tasks", "Projects", "Goals & Areas", "Notes",
    "Habits & Reviews", "Inbox", "Start Here",
)
HOME_SECTIONS = (
    "Daily Top 3", "Calendar", "Weekly priorities", "Inbox",
    "Active Projects", "Weekly plan follow-through",
)


@dataclass(frozen=True)
class Property:
    kind: str
    options: tuple[str, ...] = ()
    target: str | None = None
    single: bool = False
    expression: str | None = None


def title() -> Property:
    return Property("title")


def select(*options: str) -> Property:
    return Property("select", options)


def status(*options: str) -> Property:
    return Property("status", options)


def relation(target: str, single: bool = False) -> Property:
    return Property("relation", target=target, single=single)


def formula(expression: str) -> Property:
    return Property("formula", expression=expression)


SCHEMA: dict[str, dict[str, Property]] = {
    "Tasks": {
        "Name": title(), "Record type": select("Task", "Series"),
        "Status": status("To do", "In progress", "Waiting", "Done", "Cancelled"),
        "Commitment": select("Committed", "Someday"),
        "Priority": select("High", "Normal", "Low"),
        "Due date": Property("date"), "Plan date": Property("date"),
        "Time block": Property("date"), "Project": relation("Projects", True),
        "Standalone Area": relation("Areas", True),
        "Parent Task": relation("Tasks", True),
        "Blocked by": relation("Tasks"),
        "Waiting reason": Property("rich_text"),
        "Follow-up date": Property("date"),
        "Non-blocking for phase": Property("checkbox"),
        "Series key": Property("rich_text"), "Series": relation("Tasks", True),
        "Recurrence pattern": Property("rich_text"),
        "Recurrence rule": Property("rich_text"),
        "Generation mode": select("Native template", "Managed local generator"),
        "Recurrence start": Property("date"), "Recurrence end": Property("date"),
        "Plan / Due offset": Property("rich_text"),
        "Occurrence date": Property("date"),
        "Occurrence key": Property("rich_text"),
        "Completed at": Property("date"), "Cancelled at": Property("date"),
        "Cancellation reason": Property("rich_text"),
        "Change note": Property("rich_text"),
        "Needs attention": formula('if(prop("Status") == "Done" and empty(prop("Completed at")), "Done needs Completed at", if(prop("Status") == "Cancelled" and empty(prop("Cancelled at")), "Cancelled needs Cancelled at", if(prop("Status") == "Waiting" and empty(prop("Waiting reason")), "Waiting needs reason", "")))'),
    },
    "Projects": {
        "Name": title(),
        "Status": status("Planned", "Active", "Paused", "Done", "Cancelled"),
        "Primary Area": relation("Areas", True), "Goal": relation("Goals", True),
        "Parent Project": relation("Projects", True),
        "Definition of done": Property("rich_text"),
        "Target date": Property("date"),
        "Project kind": select("Project", "Phase"),
        "Completed at": Property("date"), "Cancelled at": Property("date"),
        "Outcome note": Property("rich_text"),
    },
    "Goals": {
        "Name": title(),
        "Status": status("Planned", "Active", "Paused", "Achieved", "Dropped"),
        "Primary Area": relation("Areas", True),
        "Review horizon": Property("date"),
        "Evidence definition": Property("rich_text"),
        "Evidence summary": Property("rich_text"),
        "Achieved at": Property("date"), "Dropped at": Property("date"),
    },
    "Areas": {
        "Name": title(), "Purpose": Property("rich_text"),
        "State": select("Active", "Archived"),
    },
    "Notes": {
        "Name": title(), "Area": relation("Areas", True),
        "Goal": relation("Goals", True), "Project": relation("Projects", True),
        "Source capture": relation("Capture Queue", True),
    },
    "Capture Queue": {
        "Name": title(), "Captured at": Property("created_time"),
        "Status": status("New", "Needs clarification", "Processed"),
        "Clarification question": Property("rich_text"),
        "Processed at": Property("date"),
    },
    "Habits": {
        "Name": title(), "Primary Area": relation("Areas", True),
        "Cadence type": select("Daily", "Selected weekdays", "N per week"),
        "Weekdays": Property("multi_select", ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")),
        "Weekly target": Property("number"),
        "Status": select("Active", "Paused", "Archived"),
        "Start date": Property("date"), "End date": Property("date"),
        "Numeric target": Property("number"), "Unit": Property("rich_text"),
        "Replaces Habit": relation("Habits", True),
    },
    "Habit Check-ins": {
        "Name": title(), "Habit": relation("Habits", True),
        "Event type": select("Check-in", "Pause started", "Pause ended"),
        "Occurrence date": Property("date"),
        "Check-in status": select("Done", "Excused"),
        "Amount": Property("number"), "Note": Property("rich_text"),
        "Event time": Property("date"), "Occurrence key": Property("rich_text"),
    },
    "Planning Log": {
        "Name": title(), "Period type": select("Daily", "Weekly", "Monthly"),
        "Period key": Property("rich_text"),
        "Start": Property("date"), "End": Property("date"),
        "State": select("Draft", "Confirmed"),
        **{f"{stage} Top {i}": relation("Tasks", True)
           for stage in ("Proposed", "Confirmed") for i in range(1, 4)},
        **{f"{stage} priority {i}": Property("rich_text")
           for stage in ("Proposed", "Confirmed") for i in range(1, 3)},
        "Summary": Property("rich_text"), "Change note": Property("rich_text"),
        "Confirmed at": Property("date"),
        "Related week": relation("Planning Log", True),
        "Confirmed slots": Property("number"),
        "Completed on planned day": Property("number"),
        "Metric needs attention": Property("rich_text"),
        "Follow-through": formula('if(prop("Confirmed slots") == 0, "No confirmed plan", format(prop("Completed on planned day")) + " / " + format(prop("Confirmed slots")))'),
    },
    "Calendar Events": {
        "Name": title(), "Kind": select("Event", "Sync health"),
        "Start": Property("date"), "End": Property("date"),
        "All day": Property("checkbox"),
        "State": select("Current", "Cancelled", "Expired"),
        "Source calendar key": Property("rich_text"),
        "Source occurrence key": Property("rich_text"),
        "Last seen at": Property("date"),
        "Last successful sync": Property("date"),
        "Sync freshness": formula('if(empty(prop("Last successful sync")), "Never synced", if(dateBetween(now(), prop("Last successful sync"), "minutes") > 30, "Stale", "Fresh"))'),
    },
}

# Inverse properties created by two-way relations; they are not separately
# declared in SCHEMA to avoid duplicate relation creation.
INVERSE_RELATIONS = {
    ("Tasks", "Parent Task"): "Children",
    ("Projects", "Parent Project"): "Children",
    ("Planning Log", "Related week"): "Days",
}


@dataclass(frozen=True)
class View:
    database: str
    name: str
    filter: dict | None = None
    sorts: tuple[dict, ...] = ()


def eq(prop: str, kind: str, value: str) -> dict:
    return {"property": prop, kind: {"equals": value}}


def one_of(*items: dict) -> dict:
    return {"or": list(items)}


def all_of(*items: dict) -> dict:
    return {"and": list(items)}


OPEN_TASK = one_of(*(eq("Status", "status", x) for x in ("To do", "In progress", "Waiting")))
TASK_BASE = all_of(eq("Record type", "select", "Task"), eq("Commitment", "select", "Committed"), OPEN_TASK)
VIEWS = (
    View("Tasks", "All"),
    View("Tasks", "Today", all_of(TASK_BASE, {"property": "Plan date", "date": {"equals": "today"}})),
    # The public filter API has no rolling fourteen-day relative value. Keep
    # this view broadly correct, then set the exact UI filter during smoke test.
    View("Tasks", "Upcoming deadlines", all_of(TASK_BASE, {"property": "Due date", "date": {"is_not_empty": True}}), ({"property": "Due date", "direction": "ascending"},)),
    View("Tasks", "Waiting", eq("Status", "status", "Waiting"), ({"property": "Follow-up date", "direction": "ascending"},)),
    View("Tasks", "Backlog", all_of(TASK_BASE, eq("Status", "status", "To do"), {"property": "Plan date", "date": {"is_empty": True}})),
    View("Tasks", "Someday", eq("Commitment", "select", "Someday")),
    View("Tasks", "Completed", one_of(eq("Status", "status", "Done"), eq("Status", "status", "Cancelled"))),
    View("Tasks", "Recurring series", eq("Record type", "select", "Series")),
    View("Tasks", "Needs attention", {"property": "Needs attention", "formula": {"string": {"is_not_empty": True}}}),
    View("Projects", "Active", eq("Status", "status", "Active")),
    View("Projects", "Planned", eq("Status", "status", "Planned")),
    View("Projects", "Paused", eq("Status", "status", "Paused")),
    View("Projects", "Completed", one_of(eq("Status", "status", "Done"), eq("Status", "status", "Cancelled"))),
    View("Goals", "Active", eq("Status", "status", "Active")),
    View("Areas", "Active", eq("State", "select", "Active")),
    View("Notes", "Recent", sorts=({"timestamp": "last_edited_time", "direction": "descending"},)),
    View("Capture Queue", "Inbox", one_of(eq("Status", "status", "New"), eq("Status", "status", "Needs clarification"))),
    View("Habits", "Current", eq("Status", "select", "Active")),
    View("Habit Check-ins", "Recent", sorts=({"property": "Event time", "direction": "descending"},)),
    View("Planning Log", "Recent", sorts=({"property": "Start", "direction": "descending"},)),
    View("Calendar Events", "Upcoming appointments", all_of(eq("Kind", "select", "Event"), eq("State", "select", "Current")), ({"property": "Start", "direction": "ascending"},)),
)
