import unittest
from datetime import date

from command_center.recurrence import occurrence_dates, occurrence_key


class RecurrenceTests(unittest.TestCase):
    def test_forward_only(self):
        rule = {"frequency": "daily", "interval": 2, "anchor": "2026-09-20"}
        self.assertEqual(occurrence_dates(rule, date(2026, 9, 29), horizon_days=3),
                         [date(2026, 9, 30), date(2026, 10, 2)])
        self.assertEqual(occurrence_key("tax", date(2026, 9, 30)), "tax:2026-09-30")

    def test_weekly_boundary(self):
        rule = {"frequency": "weekly", "interval": 1, "anchor": "2026-09-28", "weekdays": [0, 4]}
        self.assertEqual(occurrence_dates(rule, date(2026, 10, 2), horizon_days=3),
                         [date(2026, 10, 2), date(2026, 10, 5)])


if __name__ == "__main__":
    unittest.main()
