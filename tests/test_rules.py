import unittest
from datetime import date, datetime, timezone

from command_center.rules import (
    HabitDefinition, duplicate_keys, habit_consistency, last_day_of_month,
    local_date, period_key, phase_readiness, top3_follow_through, validate_task,
)


class RuleTests(unittest.TestCase):
    def test_vancouver_dst_and_periods(self):
        self.assertEqual(local_date(datetime(2026, 3, 8, 7, 30, tzinfo=timezone.utc)), date(2026, 3, 7))
        self.assertEqual(local_date(datetime(2026, 3, 8, 10, 30, tzinfo=timezone.utc)), date(2026, 3, 8))
        self.assertEqual(period_key("Weekly", date(2026, 9, 27)), "2026-09-21")
        self.assertTrue(last_day_of_month(date(2026, 5, 31)))

    def test_phase_zero_or_cancelled_not_ready(self):
        self.assertFalse(phase_readiness([])["ready_for_review"])
        self.assertFalse(phase_readiness([{"status": "Cancelled"}])["ready_for_review"])
        self.assertTrue(phase_readiness([{"status": "Done"}, {"status": "To do", "non_blocking_for_phase": True}])["ready_for_review"])

    def test_top3_final_slots_and_day_cutoff(self):
        logs = [{"period_key": "2026-09-28", "state": "Confirmed", "confirmed_top": ["a", "b"]},
                {"period_key": "2026-09-29", "state": "Draft", "confirmed_top": ["c"]}]
        tasks = {"a": {"status": "Done", "completed_at": datetime(2026, 9, 29, 6, 30, tzinfo=timezone.utc)},
                 "b": {"status": "Done", "completed_at": None}}
        result = top3_follow_through(logs, tasks, date(2026, 9, 29))
        self.assertEqual((result["completed"], result["confirmed"]), (1, 2))
        self.assertEqual(len(result["attention"]), 1)

    def test_habit_pause_excused_and_prorated_week(self):
        definition = HabitDefinition("N per week", date(2026, 9, 28), weekly_target=3)
        result = habit_consistency(definition, date(2026, 9, 28), date(2026, 10, 4),
                                   [{"date": date(2026, 9, 28), "status": "Done"},
                                    {"date": date(2026, 9, 29), "status": "Excused"},
                                    {"date": date(2026, 9, 30), "status": "Done"}],
                                   [(date(2026, 10, 1), date(2026, 10, 4))])
        self.assertEqual(result, {"done": 1, "eligible": 1})

    def test_validation_and_duplicate_keys(self):
        self.assertIn("Waiting needs a reason", validate_task({"name": "Call", "status": "Waiting"}))
        self.assertEqual(duplicate_keys([{"key": "x"}, {"key": "x"}, {"key": "y"}], "key"), ["x"])


if __name__ == "__main__":
    unittest.main()
