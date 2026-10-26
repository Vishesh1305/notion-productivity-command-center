import unittest
from datetime import date

from command_center.habits import check_in, habit_report


def prop(kind, value):
    return {"type": kind, kind: value}


class Fake:
    def __init__(self):
        self.pages = {
            "habit": {
                "id": "habit", "parent": {"data_source_id": "habits"},
                "properties": {
                    "Name": prop("title", [{"plain_text": "Read"}]),
                    "Status": prop("select", {"name": "Active"}),
                    "Cadence type": prop("select", {"name": "Daily"}),
                    "Start date": prop("date", {"start": "2026-09-01"}),
                },
            },
        }
        self.posts = []

    def query_all(self, source_id):
        return [p for p in self.pages.values() if p["parent"]["data_source_id"] == source_id]

    def request(self, method, path, body=None):
        if method == "GET":
            return self.pages[path.rsplit("/", 1)[-1]]
        if method == "POST":
            self.posts.append(body)
            page = {"id": f"checkin-{len(self.posts)}", "parent": body["parent"],
                    "properties": {name: prop(next(iter(value)), next(iter(value.values())))
                                   for name, value in body["properties"].items()}}
            self.pages[page["id"]] = page
            return page
        raise AssertionError((method, path))


class HabitTests(unittest.TestCase):
    def test_retry_and_conflicting_checkin(self):
        fake = Fake()
        day = date(2026, 9, 29)
        first = check_in(fake, "habits", "checkins", "habit", day)
        self.assertIs(check_in(fake, "habits", "checkins", "habit", day), first)
        self.assertEqual(len(fake.posts), 1)
        with self.assertRaisesRegex(ValueError, "review the correction"):
            check_in(fake, "habits", "checkins", "habit", day, "Excused")
        fake.pages["copy"] = {**first, "id": "copy"}
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            check_in(fake, "habits", "checkins", "habit", day)

    def test_cadence_and_pauses_in_report(self):
        fake = Fake()
        for day in (date(2026, 9, 28), date(2026, 9, 29)):
            check_in(fake, "habits", "checkins", "habit", day)
        pause = {
            "id": "pause", "parent": {"data_source_id": "checkins"},
            "properties": {
                "Habit": prop("relation", [{"id": "habit"}]),
                "Event type": prop("select", {"name": "Pause started"}),
                "Event time": prop("date", {"start": "2026-09-30T12:00:00+00:00"}),
            },
        }
        fake.pages["pause"] = pause
        report = habit_report(fake, "habits", "checkins", "habit",
                              date(2026, 9, 28), date(2026, 10, 1))
        self.assertEqual((report["done"], report["eligible"]), (2, 2))
        self.assertEqual(report["warnings"], [])
        fake.pages["habit"]["properties"]["Cadence type"] = prop("select", {"name": "Selected weekdays"})
        fake.pages["habit"]["properties"]["Weekdays"] = prop("multi_select", [{"name": "Mon"}])
        with self.assertRaisesRegex(ValueError, "selected weekdays"):
            check_in(fake, "habits", "checkins", "habit", date(2026, 10, 2))

    def test_native_button_key_matches_cli_retry(self):
        fake = Fake()
        habit_id = "12345678-1234-1234-1234-123456789abc"
        fake.pages[habit_id] = {**fake.pages.pop("habit"), "id": habit_id}
        day = date(2026, 10, 1)
        native = {
            "id": "native", "parent": {"data_source_id": "checkins"},
            "properties": {
                "Habit": prop("relation", [{"id": habit_id}]),
                "Event type": prop("select", {"name": "Check-in"}),
                "Check-in status": prop("select", {"name": "Done"}),
                "Occurrence key": prop("rich_text", [{"plain_text":
                    "12345678123412341234123456789abc:2026-10-01"}]),
                "Note": prop("rich_text", []),
            },
        }
        fake.pages["native"] = native
        self.assertIs(check_in(fake, "habits", "checkins", habit_id, day), native)
        self.assertEqual(fake.posts, [])


if __name__ == "__main__":
    unittest.main()
