"""Operator commands. Structural writes require the explicit `apply` verb."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from .calendar_mirror import apple_export, calendar_window, sync_calendar
from .ddl import create_table, relation_updates
from .definitions import SCHEMA
from .habits import check_in, habit_report
from .metrics import refresh_week_metric
from .notion import NotionClient
from .operations import cancel_task, complete_task, confirm_day, confirm_week, draft_review, quick_add, set_waiting
from .recurrence import generate
from .rules import local_date
from .seed import seed_approved
from .setup import Reconciler, load_manifest, plan_offline, structural_plan


def main() -> None:
    parser = argparse.ArgumentParser(prog="command-center")
    parser.add_argument("--manifest", type=Path, default=Path("manifest.json"))
    sub = parser.add_subparsers(dest="command", required=True)
    plan_parser = sub.add_parser("plan", help="Offline structural dry-run")
    plan_parser.add_argument("--json", action="store_true", help="Show exact schema and view definitions")
    sub.add_parser("ddl", help="Show connector DDL for database creation and relation pass")
    sub.add_parser("inspect", help="Live, read-only structural plan")
    sub.add_parser("apply", help="Explicit additive structural update")
    sub.add_parser("seed", help="Seed approved Areas and Planned ATLAS chain")
    sub.add_parser("calendars", help="List Apple calendars; requests macOS permission")
    sub.add_parser("sync-calendar", help="Mirror selected calendars into Notion")
    sub.add_parser("generate-recurrence", help="Create forward managed Task occurrences")
    habit_checkin_parser = sub.add_parser("habit-checkin", help="Record a retry-safe Habit Done or Excused check-in")
    habit_checkin_parser.add_argument("habit_id")
    habit_checkin_parser.add_argument("day", type=date.fromisoformat)
    habit_checkin_parser.add_argument("--status", choices=("Done", "Excused"), default="Done")
    habit_checkin_parser.add_argument("--amount", type=float)
    habit_checkin_parser.add_argument("--note", default="")
    habit_report_parser = sub.add_parser("habit-report", help="Read Habit consistency for a date range")
    habit_report_parser.add_argument("habit_id")
    habit_report_parser.add_argument("start", type=date.fromisoformat)
    habit_report_parser.add_argument("end", type=date.fromisoformat)
    capture_parser = sub.add_parser("capture", help="Save raw text immediately to Capture Queue")
    capture_parser.add_argument("text")
    done_parser = sub.add_parser("done", help="Canonical Task Done action")
    done_parser.add_argument("task_id")
    cancel_parser = sub.add_parser("cancel", help="Cancel a Task with reason and timestamp")
    cancel_parser.add_argument("task_id")
    cancel_parser.add_argument("reason")
    waiting_parser = sub.add_parser("waiting", help="Set Task Waiting with a reason")
    waiting_parser.add_argument("task_id")
    waiting_parser.add_argument("reason")
    day_parser = sub.add_parser("confirm-day", help="Confirm one to three selected Tasks")
    day_parser.add_argument("day", type=date.fromisoformat)
    day_parser.add_argument("task_ids", nargs="+")
    day_parser.add_argument("--change-note", default="")
    week_parser = sub.add_parser("confirm-week", help="Confirm one or two weekly priorities")
    week_parser.add_argument("day", type=date.fromisoformat)
    week_parser.add_argument("priorities", nargs="+")
    week_parser.add_argument("--change-note", default="")
    review_parser = sub.add_parser("draft-review", help="Create a Sunday or month-end draft log")
    review_parser.add_argument("kind", choices=("Weekly", "Monthly"))
    review_parser.add_argument("day", type=date.fromisoformat)
    metric_parser = sub.add_parser("refresh-metric", help="Refresh a week's confirmed Top 3 follow-through count")
    metric_parser.add_argument("day", type=date.fromisoformat, nargs="?",
                               default=local_date(datetime.now(timezone.utc)))
    args = parser.parse_args()
    if args.command == "plan":
        if args.json:
            print(json.dumps(structural_plan(), indent=2))
        else:
            for line in plan_offline():
                print(line)
        return
    if args.command == "ddl":
        for name in SCHEMA:
            print(f"{name}: {create_table(name)}")
        existing = load_manifest(args.manifest).get("databases", {})
        sources = {name: info["data_source_id"] for name, info in existing.items()}
        if len(sources) == len(SCHEMA):
            for name in SCHEMA:
                if statement := relation_updates(name, sources):
                    print(f"{name} relations: {statement}")
        else:
            print("Relation statements appear after all ten data source IDs are recorded in manifest.json.")
        return
    if args.command == "calendars":
        import subprocess
        exporter = Path(__file__).resolve().parents[2] / "macos" / "calendar-export.sh"
        result = subprocess.run([str(exporter), "--list"], check=False, text=True, capture_output=True, timeout=90)
        if result.returncode:
            detail = result.stderr.strip() or "Calendar access failed"
            raise SystemExit(detail)
        for row in json.loads(result.stdout):
            print(f"{row['title']} ({row['source']}): {row['id']}")
        return
    manifest = load_manifest(args.manifest)
    client = NotionClient()
    if args.command in ("inspect", "apply"):
        runner = Reconciler(client, manifest, args.manifest)
        for line in runner.run(apply=args.command == "apply"):
            print(line)
        return
    if args.command == "seed":
        if len(manifest.get("databases", {})) != 10:
            raise ValueError("Apply and inspect the ten databases before seeding")
        print(json.dumps(seed_approved(client, manifest["databases"]), indent=2))
        return
    if args.command == "capture":
        page = quick_add(client, manifest["databases"]["Capture Queue"]["data_source_id"], args.text)
        print(page.get("url", page["id"]))
        return
    if args.command == "done":
        page = complete_task(client, manifest["databases"]["Tasks"]["data_source_id"], args.task_id)
        print(page.get("url", page["id"]))
        return
    if args.command == "cancel":
        page = cancel_task(client, manifest["databases"]["Tasks"]["data_source_id"], args.task_id, args.reason)
        print(page.get("url", page["id"]))
        return
    if args.command == "waiting":
        page = set_waiting(client, manifest["databases"]["Tasks"]["data_source_id"], args.task_id, args.reason)
        print(page.get("url", page["id"]))
        return
    if args.command == "confirm-day":
        page = confirm_day(client, manifest["databases"]["Tasks"]["data_source_id"],
                           manifest["databases"]["Planning Log"]["data_source_id"],
                           args.day, args.task_ids, args.change_note)
        print(page.get("url", page["id"]))
        return
    if args.command == "confirm-week":
        page = confirm_week(client, manifest["databases"]["Planning Log"]["data_source_id"],
                            args.day, args.priorities, args.change_note)
        print(page.get("url", page["id"]))
        return
    if args.command == "draft-review":
        page = draft_review(client, manifest["databases"]["Planning Log"]["data_source_id"],
                            args.kind, args.day)
        print(page.get("url", page["id"]))
        return
    if args.command == "refresh-metric":
        result = refresh_week_metric(client, manifest["databases"]["Tasks"]["data_source_id"],
                                     manifest["databases"]["Planning Log"]["data_source_id"], args.day)
        if result is None:
            print("No Weekly Log for this Vancouver week; no metric record was created.")
        else:
            print(json.dumps({"url": result["page"].get("url", result["page"]["id"]),
                              "completed": result["completed"], "confirmed": result["confirmed"],
                              "attention": result["attention"], "changed": result["changed"]}, indent=2))
        return
    if args.command == "generate-recurrence":
        source_id = manifest["databases"]["Tasks"]["data_source_id"]
        print(json.dumps(generate(client, source_id, local_date(datetime.now(timezone.utc))), indent=2))
        return
    if args.command == "habit-checkin":
        page = check_in(client, manifest["databases"]["Habits"]["data_source_id"],
                        manifest["databases"]["Habit Check-ins"]["data_source_id"],
                        args.habit_id, args.day, args.status, amount=args.amount, note=args.note)
        print(page.get("url", page["id"]))
        return
    if args.command == "habit-report":
        print(json.dumps(habit_report(client, manifest["databases"]["Habits"]["data_source_id"],
                                      manifest["databases"]["Habit Check-ins"]["data_source_id"],
                                      args.habit_id, args.start, args.end), indent=2))
        return
    if args.command == "sync-calendar":
        selected = manifest.get("selected_calendar_ids", [])
        if not selected:
            raise ValueError("Set selected_calendar_ids in manifest.json after listing calendars")
        source_id = manifest["databases"]["Calendar Events"]["data_source_id"]
        now = datetime.now(timezone.utc)
        exporter = Path(__file__).resolve().parents[2] / "macos" / "calendar-export.sh"
        start, end = calendar_window(now)
        events = apple_export(exporter, selected, start, end)
        print(json.dumps(sync_calendar(client, source_id, events, now=now), indent=2))


if __name__ == "__main__":
    main()
