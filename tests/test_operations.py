import unittest
from datetime import date, datetime, timezone

from command_center.notion import AmbiguousWrite
from command_center.operations import (
    cancel_task, complete_task, confirm_day, confirm_week, draft_review,
    quick_add, set_waiting,
)


class OperationsFake:
    def __init__(self):
        self.pages = {
            "task": {"id": "task", "parent": {"data_source_id": "tasks"},
                     "properties": {"Status": {"type": "status", "status": {"name": "To do"}},
                                    "Commitment": {"type": "select", "select": {"name": "Committed"}}}}
        }
        self.posts = []
        self.fail_daily_patch = False

    def query_all(self, source_id):
        return [x for x in self.pages.values() if x.get("parent", {}).get("data_source_id") == source_id]

    def request(self, method, path, body=None):
        if method == "GET" and path.startswith("/pages/"):
            return self.pages[path.split("/")[-1]]
        if method == "POST" and path == "/pages":
            self.posts.append(body)
            title = body["properties"]["Name"]["title"][0]["text"]["content"]
            id_ = str(len(self.posts))
            props = dict(body["properties"])
            for value in props.values():
                value["type"] = next(iter(value))
            result = {"id": id_, "parent": body["parent"], "properties": props, "title": title}
            self.pages[id_] = result
            return result
        if method == "PATCH" and path.startswith("/pages/"):
            if self.fail_daily_patch:
                raise AmbiguousWrite("simulated")
            page = self.pages[path.split("/")[-1]]
            page["properties"].update(body["properties"])
            for value in page["properties"].values():
                value["type"] = next(iter(value))
            return page
        raise AssertionError((method, path))


class OperationTests(unittest.TestCase):
    def test_capture_preserves_raw_text(self):
        fake = OperationsFake()
        quick_add(fake, "captures", "Line one\nLine two")
        self.assertEqual(fake.posts[0]["children"][0]["paragraph"]["rich_text"][0]["text"]["content"],
                         "Line one\nLine two")

    def test_waiting_requires_reason(self):
        fake = OperationsFake()
        with self.assertRaises(ValueError):
            set_waiting(fake, "tasks", "task", " ")

    def test_confirm_day_partial_failure_can_retry_without_duplicate_logs(self):
        fake = OperationsFake()
        fake.fail_daily_patch = True
        with self.assertRaises(AmbiguousWrite):
            confirm_day(fake, "tasks", "logs", date(2026, 9, 29), ["task"])
        self.assertEqual(len(fake.posts), 2)
        fake.fail_daily_patch = False
        confirm_day(fake, "tasks", "logs", date(2026, 9, 29), ["task"])
        self.assertEqual(len(fake.posts), 2)

    def test_confirm_day_retry_after_task_completion_and_replan_gate(self):
        fake = OperationsFake()
        day = date(2026, 9, 29)
        daily = confirm_day(fake, "tasks", "logs", day, ["task"])
        complete_task(fake, "tasks", "task", datetime(2026, 9, 30, tzinfo=timezone.utc))
        self.assertIs(confirm_day(fake, "tasks", "logs", day, ["task"]), daily)
        fake.pages["other"] = {"id": "other", "parent": {"data_source_id": "tasks"},
                               "properties": {"Status": {"type": "status", "status": {"name": "To do"}},
                                              "Commitment": {"type": "select", "select": {"name": "Committed"}}}}
        with self.assertRaisesRegex(ValueError, "change note"):
            confirm_day(fake, "tasks", "logs", day, ["other"])
        updated = confirm_day(fake, "tasks", "logs", day, ["other"], "Replaced completed item")
        self.assertEqual(updated["properties"]["Confirmed Top 1"]["relation"][0]["id"], "other")
        self.assertEqual(len(fake.posts), 2)

    def test_done_without_timestamp_requires_correction_and_cancel_requires_reason(self):
        fake = OperationsFake()
        fake.pages["task"]["properties"]["Status"]["status"]["name"] = "Done"
        with self.assertRaisesRegex(ValueError, "actual completion time"):
            complete_task(fake, "tasks", "task")
        fake.pages["task"]["properties"]["Status"]["status"]["name"] = "To do"
        with self.assertRaises(ValueError):
            cancel_task(fake, "tasks", "task", " ")
        cancelled = cancel_task(fake, "tasks", "task", "No longer needed")
        self.assertEqual(cancelled["properties"]["Status"]["status"]["name"], "Cancelled")
        self.assertIs(cancel_task(fake, "tasks", "task", "No longer needed"), cancelled)
        with self.assertRaisesRegex(ValueError, "reviewed correction"):
            cancel_task(fake, "tasks", "task", "Different reason")

    def test_week_priorities_and_distinct_sunday_month_end_reviews(self):
        fake = OperationsFake()
        day = date(2026, 5, 31)  # Sunday and last calendar day.
        with self.assertRaises(ValueError):
            confirm_week(fake, "logs", day, ["One", "Two", "Three"])
        weekly = confirm_week(fake, "logs", day, ["Portfolio", "Health"])
        self.assertIs(confirm_week(fake, "logs", day, ["Portfolio", "Health"]), weekly)
        with self.assertRaisesRegex(ValueError, "change note"):
            confirm_week(fake, "logs", day, ["Portfolio"])
        confirm_week(fake, "logs", day, ["Portfolio"], "Narrowed scope")
        self.assertIs(draft_review(fake, "logs", "Weekly", day), weekly)
        monthly = draft_review(fake, "logs", "Monthly", day)
        self.assertNotEqual(monthly["id"], weekly["id"])
        self.assertIs(draft_review(fake, "logs", "Monthly", day), monthly)
        self.assertEqual(len(fake.posts), 2)
        with self.assertRaises(ValueError):
            draft_review(fake, "logs", "Weekly", date(2026, 6, 1))


if __name__ == "__main__":
    unittest.main()
