import tempfile
import unittest
from pathlib import Path

from command_center.definitions import SCHEMA
from command_center.notion import NotionClient
from command_center.setup import Reconciler, plan_offline, unique_child


class FakeNotion:
    def __init__(self):
        self.objects = {"parent": []}
        self.db = {}
        self.sources = {}
        self.views = {}
        self.next_id = 0

    def identity(self):
        self.next_id += 1
        return str(self.next_id)

    def pages(self, parent):
        return self.objects.get(parent, [])

    def list_views(self, database):
        return self.views.get(database, [])

    def query_all(self, source):
        return []

    def block_tree(self, page_id):
        return []

    def request(self, method, path, body=None):
        if method == "GET" and path.startswith("/pages/"):
            return {"id": path.split("/")[-1]}
        if method == "GET" and path.startswith("/databases/"):
            return self.db[path.split("/")[-1]]
        if method == "GET" and path.startswith("/data_sources/"):
            return self.sources[path.split("/")[-1]]
        if method == "POST" and path == "/pages":
            parent = body["parent"]["page_id"]
            name = body["properties"]["title"]["title"][0]["text"]["content"]
            obj = {"id": self.identity(), "type": "child_page", "child_page": {"title": name}}
            self.objects.setdefault(parent, []).append(obj)
            return obj
        if method == "POST" and path == "/databases":
            parent = body["parent"]["page_id"]
            name = body["title"][0]["text"]["content"]
            id_, source_id = self.identity(), self.identity()
            obj = {"id": id_, "data_sources": [{"id": source_id}]}
            self.db[id_] = obj
            self.sources[source_id] = {"id": source_id, "properties": {"Name": {"type": "title"}}}
            self.objects.setdefault(parent, []).append({"id": id_, "type": "child_database", "child_database": {"title": name}})
            return obj
        if method == "PATCH" and path.startswith("/data_sources/"):
            source = self.sources[path.split("/")[-1]]
            for name, value in body["properties"].items():
                source["properties"][name] = {"type": next(iter(value))}
            return source
        if method == "POST" and path == "/views":
            obj = {"id": self.identity(), "name": body["name"]}
            self.views.setdefault(body["database_id"], []).append(obj)
            return obj
        raise AssertionError((method, path, body))


class SetupTests(unittest.TestCase):
    def test_view_listing_hydrates_stubs_and_follows_cursor(self):
        client = NotionClient("test-token")
        calls = []

        def request(method, path, body=None, query=None):
            calls.append((method, path, query))
            if path == "/views" and query == {"database_id": "db"}:
                return {"results": [{"object": "view", "id": "one"}], "next_cursor": "next"}
            if path == "/views" and query == {"database_id": "db", "start_cursor": "next"}:
                return {"results": [{"id": "two", "name": "Second"}], "next_cursor": None}
            if path == "/views/one":
                return {"id": "one", "name": "First"}
            raise AssertionError((method, path, query))

        client.request = request
        self.assertEqual([view["name"] for view in client.list_views("db")], ["First", "Second"])
        self.assertEqual([path for _, path, _ in calls], ["/views", "/views/one", "/views"])

    def test_rerun_does_not_duplicate(self):
        fake = FakeNotion()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            runner = Reconciler(fake, {"parent_page_id": "parent"}, path)
            first = runner.run(apply=True)
            second = runner.run(apply=True)
            self.assertTrue(first)
            self.assertEqual(second, [])
            self.assertEqual(len(fake.db), len(SCHEMA))

    def test_duplicate_scoped_name_stops(self):
        children = [{"type": "child_page", "child_page": {"title": "Home"}}] * 2
        with self.assertRaises(ValueError):
            unique_child(children, "child_page", "Home")

    def test_layout_toggle_does_not_duplicate_sources_on_recovery(self):
        fake = FakeNotion()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            runner = Reconciler(fake, {"parent_page_id": "parent"}, path)
            runner.run(apply=True)
            root = runner.manifest["root_page_id"]
            fake.objects["library"] = fake.objects[root]
            fake.objects[root] = [{"id": "library", "type": "toggle", "has_children": True}]
            runner.manifest["pages"] = {}
            runner.manifest["databases"] = {}
            self.assertEqual(runner.run(apply=True), [])
            self.assertEqual(len(fake.db), len(SCHEMA))


if __name__ == "__main__":
    unittest.main()
