import unittest

from command_center.ddl import create_table, relation_updates
from command_center.definitions import SCHEMA


class DDLTests(unittest.TestCase):
    def test_sync_freshness_formula_is_in_versioned_schema(self):
        self.assertEqual(SCHEMA["Calendar Events"]["Sync freshness"].kind, "formula")
        self.assertIn('"Sync freshness" FORMULA(', create_table("Calendar Events"))

    def test_every_database_has_title_and_relation_second_pass(self):
        sources = {name: name.lower().replace(" ", "-") for name in SCHEMA}
        for name in SCHEMA:
            ddl = create_table(name)
            self.assertIn('"Name" TITLE', ddl)
            self.assertNotIn("RELATION", ddl)
            relations = relation_updates(name, sources)
            self.assertEqual(relations.count("ADD COLUMN"),
                             sum(p.kind == "relation" for p in SCHEMA[name].values()))


if __name__ == "__main__":
    unittest.main()
