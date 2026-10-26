import unittest
from datetime import date

from command_center.metrics import refresh_week_metric
from command_center.notion import AmbiguousWrite


def text(value):
    return {"type": "rich_text", "rich_text": [{"plain_text": value}]}


def select(value):
    return {"type": "select", "select": {"name": value}}


class MetricFake:
    def __init__(self):
        self.pages = {
            "week": {"id": "week", "parent": {"data_source_id": "logs"}, "properties": {
                "Period type": select("Weekly"), "Period key": text("2026-09-28")}},
            "day": {"id": "day", "parent": {"data_source_id": "logs"}, "properties": {
                "Period type": select("Daily"), "Period key": text("2026-09-29"),
                "State": select("Confirmed"),
                "Confirmed Top 1": {"relation": [{"id": "on-time"}]},
                "Confirmed Top 2": {"relation": [{"id": "missing-stamp"}]}}},
            "on-time": {"id": "on-time", "parent": {"data_source_id": "tasks"}, "properties": {
                "Status": {"type": "status", "status": {"name": "Done"}},
                "Completed at": {"date": {"start": "2026-09-30T01:00:00+00:00"}}}},
            "missing-stamp": {"id": "missing-stamp", "parent": {"data_source_id": "tasks"}, "properties": {
                "Status": {"type": "status", "status": {"name": "Done"}}}},
        }
        self.patches = 0
        self.ambiguous = False

    def query_all(self, source_id):
        return [row for row in self.pages.values()
                if row["parent"]["data_source_id"] == source_id]

    def request(self, method, path, body=None):
        row = self.pages[path.split("/")[-1]]
        if method == "GET":
            return row
        if method == "PATCH":
            self.patches += 1
            row["properties"].update(body["properties"])
            for value in body["properties"].values():
                value["type"] = next(iter(value))
            if self.ambiguous:
                raise AmbiguousWrite("response lost after write")
            return row
        raise AssertionError((method, path))


class MetricTests(unittest.TestCase):
    def test_vancouver_count_attention_and_retry_safe_refresh(self):
        fake = MetricFake()
        fake.ambiguous = True
        result = refresh_week_metric(fake, "tasks", "logs", date(2026, 9, 30))
        self.assertEqual((result["completed"], result["confirmed"]), (1, 2))
        self.assertIn("Done without Completed at", result["attention"][0])
        self.assertEqual(fake.patches, 1)
        result = refresh_week_metric(fake, "tasks", "logs", date(2026, 9, 30))
        self.assertFalse(result["changed"])
        self.assertEqual(fake.patches, 1)

    def test_duplicate_daily_key_refuses_to_count_twice(self):
        fake = MetricFake()
        fake.pages["duplicate"] = {**fake.pages["day"], "id": "duplicate"}
        with self.assertRaisesRegex(ValueError, "Duplicate Daily Planning Log"):
            refresh_week_metric(fake, "tasks", "logs", date(2026, 9, 30))


if __name__ == "__main__":
    unittest.main()
