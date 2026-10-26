import unittest
from datetime import datetime, timedelta, timezone

from command_center.calendar_mirror import CalendarEvent, calendar_window, event_properties, mirror_plan, stale, sync_calendar
from command_center.rules import ZONE


class SyncFake:
    def __init__(self, fail_event_write=False):
        self.fail_event_write = fail_event_write
        self.pages = []

    def query_all(self, source_id):
        return list(self.pages)

    def request(self, method, path, body):
        if self.fail_event_write and body["properties"].get("Kind", {}).get("select", {}).get("name") == "Event":
            raise RuntimeError("simulated partial sync")
        props = body["properties"]
        for value in props.values():
            value["type"] = next(iter(value))
        if method == "POST":
            page = {"id": str(len(self.pages) + 1), "properties": props}
            self.pages.append(page)
            return page
        if method == "PATCH":
            page = next(p for p in self.pages if p["id"] == path.split("/")[-1])
            page["properties"].update(props)
            return page
        raise AssertionError((method, path))


class MirrorTests(unittest.TestCase):
    def test_window_uses_vancouver_days_across_dst(self):
        now = datetime(2026, 3, 8, 18, tzinfo=timezone.utc)
        start, end = calendar_window(now)
        self.assertEqual(start.astimezone(ZONE).isoformat(), "2026-03-07T00:00:00-08:00")
        self.assertEqual(end.astimezone(ZONE).isoformat(), "2026-03-23T00:00:00-07:00")
        self.assertEqual(end - start, timedelta(days=16, hours=-1))

    def test_reschedule_is_update_and_failed_fetch_does_not_expire(self):
        previous = [{"id": "p", "key": "calendar:event", "calendar_key": "calendar",
                     "title": "Meeting", "start": "2026-10-01T03:00:00",
                     "start_zone": "America/Vancouver", "end": "2026-10-01T04:00:00",
                     "end_zone": "America/Vancouver", "all_day": False,
                     "state": "Current"}]
        moved = CalendarEvent("calendar:event", "calendar", "Meeting",
                              "2026-10-01T12:00:00+00:00", "2026-10-01T13:00:00+00:00", False)
        self.assertEqual(len(mirror_plan(previous, [moved], complete=True)["updates"]), 1)
        unchanged = CalendarEvent("calendar:event", "calendar", "Meeting",
                                  "2026-10-01T10:00:00+00:00", "2026-10-01T11:00:00+00:00", False)
        self.assertEqual(len(mirror_plan(previous, [unchanged], complete=True)["touches"]), 1)
        legacy = {**previous[0], "start": unchanged.start, "end": unchanged.end,
                  "start_zone": None, "end_zone": None}
        self.assertEqual(len(mirror_plan([legacy], [unchanged], complete=True)["updates"]), 1)
        self.assertEqual(mirror_plan(previous, [], complete=False)["inactivates"], [])
        self.assertEqual(len(mirror_plan(previous, [], complete=True)["inactivates"]), 1)

    def test_timed_events_write_vancouver_offset_without_changing_instant(self):
        event = CalendarEvent("key", "calendar", "Meeting",
                              "2026-10-29T21:00:00.000Z", "2026-10-30T04:15:00.000Z", False)
        props = event_properties(event, "2026-10-25T23:00:00+00:00")
        self.assertEqual(props["Start"]["date"],
                         {"start": "2026-10-29T14:00:00.000-07:00"})
        self.assertEqual(props["End"]["date"],
                         {"start": "2026-10-29T21:15:00.000-07:00"})

    def test_repeated_fall_back_hour_preserves_offset(self):
        first = CalendarEvent("first", "calendar", "First", "2025-11-02T08:30:00Z",
                              "2025-11-02T08:45:00Z", False)
        second = CalendarEvent("second", "calendar", "Second", "2025-11-02T09:30:00Z",
                               "2025-11-02T09:45:00Z", False)
        self.assertEqual(event_properties(first, "2025-10-25T23:00:00Z")["Start"]["date"],
                         {"start": "2025-11-02T01:30:00.000-07:00"})
        self.assertEqual(event_properties(second, "2025-10-25T23:00:00Z")["Start"]["date"],
                         {"start": "2025-11-02T01:30:00.000-08:00"})

    def test_vancouver_remains_utc_minus_seven_after_november_2026(self):
        event = CalendarEvent("key", "calendar", "Meeting", "2026-11-02T09:30:00Z",
                              "2026-11-02T09:45:00Z", False)
        self.assertEqual(event_properties(event, "2026-10-25T23:00:00Z")["Start"]["date"],
                         {"start": "2026-11-02T02:30:00.000-07:00"})

    def test_freshness(self):
        now = datetime(2026, 9, 29, 12, tzinfo=timezone.utc)
        self.assertTrue(stale(None, now))
        self.assertFalse(stale(now - timedelta(minutes=30), now))
        self.assertTrue(stale(now - timedelta(minutes=31), now))

    def test_sync_health_only_advances_after_all_event_writes(self):
        event = CalendarEvent("calendar:event", "calendar", "Meeting",
                              "2026-10-01T12:00:00+00:00", "2026-10-01T13:00:00+00:00", False)
        now = datetime(2026, 9, 29, 12, tzinfo=timezone.utc)
        fake = SyncFake(fail_event_write=True)
        with self.assertRaisesRegex(RuntimeError, "partial sync"):
            sync_calendar(fake, "calendar-events", [event], now=now)
        self.assertEqual(fake.pages, [])
        fake.fail_event_write = False
        sync_calendar(fake, "calendar-events", [event], now=now)
        self.assertEqual(len(fake.pages), 2)
        health = next(p for p in fake.pages if p["properties"]["Kind"]["select"]["name"] == "Sync health")
        self.assertEqual(health["properties"]["Last successful sync"]["date"]["start"], now.isoformat())
        later = now + timedelta(minutes=15)
        self.assertEqual(sync_calendar(fake, "calendar-events", [event], now=later)["seen"], ["1"])
        appointment = next(p for p in fake.pages if p["properties"]["Kind"]["select"]["name"] == "Event")
        self.assertEqual(appointment["properties"]["Last seen at"]["date"]["start"], later.isoformat())


if __name__ == "__main__":
    unittest.main()
