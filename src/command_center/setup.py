"""Additive structural reconciliation for the command center."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .definitions import HOME_SECTIONS, INVERSE_RELATIONS, PAGES, SCHEMA, VIEWS, Property
from .notion import AmbiguousWrite, NotionClient, plain, rich_text

ROOT_NAME = "Productivity Command Center"


def scoped_children(client: NotionClient, root: str, *, max_depth: int = 5,
                    budget: int = 1_000) -> list[dict]:
    """Find owned pages/databases in the root's presentation containers.

    Dashboard callouts and toggles may contain the original child blocks. Do
    not descend into child pages or databases: those are separate workspaces.
    """
    containers = {"toggle", "heading_1", "heading_2", "heading_3",
                  "callout", "column_list", "column", "synced_block"}
    found: list[dict] = []
    seen: set[str] = set()

    def walk(block_id: str, depth: int) -> None:
        if depth > max_depth:
            raise ValueError("Command center layout nesting exceeds discovery limit")
        if block_id in seen:
            return
        seen.add(block_id)
        blocks = client.pages(block_id)
        found.extend(blocks)
        if len(found) > budget:
            raise ValueError("Command center layout exceeds discovery limit")
        for block in blocks:
            if block.get("type") in containers and block.get("has_children"):
                walk(block["id"], depth + 1)

    walk(root, 0)
    return found


def child_title(block: dict) -> str | None:
    kind = block.get("type")
    if kind in ("child_page", "child_database"):
        return block.get(kind, {}).get("title")
    return None


def unique_child(children: list[dict], kind: str, name: str) -> dict | None:
    found = [x for x in children if x.get("type") == kind and child_title(x) == name]
    if len(found) > 1:
        raise ValueError(f"Duplicate scoped {kind}: {name}; resolve before apply")
    return found[0] if found else None


def property_body(prop: Property, sources: dict[str, str], *, inverse: str | None = None) -> dict:
    kind = prop.kind
    if kind == "relation":
        target = sources.get(prop.target or "")
        if not target:
            raise ValueError(f"Missing target data source: {prop.target}")
        return {"relation": {"data_source_id": target,
                             **({"dual_property": {"synced_property_name": inverse}}
                                if inverse else {"single_property": {}})}}
    if kind in ("select", "multi_select", "status"):
        return {kind: {"options": [{"name": x} for x in prop.options]}}
    if kind == "formula":
        return {"formula": {"expression": prop.expression}}
    return {kind: {}}


def plan_offline() -> list[str]:
    operations = [f"create root page: {ROOT_NAME}"]
    operations.extend(f"create page: {name}" for name in PAGES)
    operations.extend(f"create database: {name}" for name in SCHEMA)
    operations.extend(f"add properties: {name} ({len(props)})" for name, props in SCHEMA.items())
    operations.extend(f"create view: {view.database} / {view.name}" for view in VIEWS)
    operations.extend(f"create Home section: {name}" for name in HOME_SECTIONS)
    return operations


def structural_plan() -> dict:
    """Reviewable schema/view plan independent of live workspace state."""
    return {
        "root": ROOT_NAME,
        "pages": list(PAGES),
        "home_sections": list(HOME_SECTIONS),
        "databases": {
            name: {field: {"type": prop.kind, "options": list(prop.options),
                           "relation_target": prop.target, "single": prop.single,
                           "expression": prop.expression}
                   for field, prop in fields.items()}
            for name, fields in SCHEMA.items()
        },
        "views": [{"database": v.database, "name": v.name,
                   "filter": v.filter, "sorts": list(v.sorts)} for v in VIEWS],
        "inverse_relations": {f"{database}.{field}": inverse
                              for (database, field), inverse in INVERSE_RELATIONS.items()},
        "policy": {"schema": "additive", "apply": "explicit",
                   "data_seed": "separate", "destructive_migration": "not supported"},
    }


class Reconciler:
    def __init__(self, client: NotionClient, manifest: dict, manifest_path: Path):
        self.client, self.manifest, self.manifest_path = client, manifest, manifest_path
        self.manifest.setdefault("pages", {})
        self.manifest.setdefault("databases", {})
        self.manifest.setdefault("views", {})

    def save(self) -> None:
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.manifest_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.manifest, indent=2, sort_keys=True) + "\n")
        tmp.replace(self.manifest_path)

    def resolve_root(self, *, apply: bool) -> str | None:
        root = self.manifest.get("root_page_id")
        if root:
            self.client.request("GET", f"/pages/{root}")
            return root
        parent = self.manifest.get("parent_page_id")
        if not parent:
            raise ValueError("manifest.json needs parent_page_id or root_page_id")
        child = unique_child(self.client.pages(parent), "child_page", ROOT_NAME)
        if child:
            root = child["id"]
        elif apply:
            try:
                page = self.client.request("POST", "/pages", {
                    "parent": {"type": "page_id", "page_id": parent},
                    "properties": {"title": {"type": "title", "title": rich_text(ROOT_NAME)}},
                })
            except AmbiguousWrite:
                child = unique_child(self.client.pages(parent), "child_page", ROOT_NAME)
                if not child:
                    raise
                page = child
            root = page["id"]
        else:
            return None
        self.manifest["root_page_id"] = root
        self.save()
        return root

    def resolve_pages(self, root: str, *, apply: bool) -> list[str]:
        changes = []
        children = scoped_children(self.client, root)
        for name in PAGES:
            saved = self.manifest["pages"].get(name)
            page = None
            if saved:
                try:
                    page = self.client.request("GET", f"/pages/{saved}")
                except Exception:
                    raise ValueError(f"Saved page ID is inaccessible: {name}") from None
            if not page:
                page = unique_child(children, "child_page", name)
            if not page:
                changes.append(f"create page: {name}")
                if apply:
                    try:
                        page = self.client.request("POST", "/pages", {
                            "parent": {"type": "page_id", "page_id": root},
                            "properties": {"title": {"type": "title", "title": rich_text(name)}},
                        })
                    except AmbiguousWrite:
                        page = unique_child(scoped_children(self.client, root), "child_page", name)
                        if not page:
                            raise
            if page:
                self.manifest["pages"][name] = page["id"]
                self.save()
        return changes

    def resolve_databases(self, root: str, *, apply: bool) -> list[str]:
        changes = []
        children = scoped_children(self.client, root)
        for name in SCHEMA:
            saved = self.manifest["databases"].get(name, {})
            database = None
            if saved.get("database_id"):
                database = self.client.request("GET", f"/databases/{saved['database_id']}")
            if not database:
                database = unique_child(children, "child_database", name)
                if database:
                    database = self.client.request("GET", f"/databases/{database['id']}")
            if not database:
                changes.append(f"create database: {name}")
                if apply:
                    try:
                        database = self.client.request("POST", "/databases", {
                            "parent": {"type": "page_id", "page_id": root},
                            "title": rich_text(name),
                            "initial_data_source": {"properties": {"Name": {"title": {}}}},
                        })
                    except AmbiguousWrite:
                        child = unique_child(scoped_children(self.client, root), "child_database", name)
                        if not child:
                            raise
                        database = self.client.request("GET", f"/databases/{child['id']}")
            if database:
                source_list = database.get("data_sources", [])
                if len(source_list) != 1:
                    raise ValueError(f"{name} must have exactly one data source")
                self.manifest["databases"][name] = {
                    "database_id": database["id"],
                    "data_source_id": source_list[0]["id"],
                }
                self.save()
        return changes

    def snapshot_source(self, name: str, source: dict) -> Path:
        """Local schema and complete data export before modifying populated schema."""
        source_id = source["id"]
        rows = self.client.query_all(source_id)
        page_contents = {row["id"]: self.client.block_tree(row["id"]) for row in rows}
        destination = self.manifest_path.parent / "exports"
        destination.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = destination / f"{name.replace(' ', '-')}-{stamp}.json"
        path.write_text(json.dumps({"source": source, "rows": rows,
                                    "page_contents": page_contents}, indent=2))
        saved = json.loads(path.read_text())
        if saved.get("source", {}).get("id") != source_id or len(saved["rows"]) != len(rows) \
                or len(saved["page_contents"]) != len(rows):
            raise RuntimeError("Snapshot verification failed")
        return path

    def reconcile_properties(self, *, apply: bool) -> list[str]:
        changes = []
        sources = {name: item["data_source_id"] for name, item in self.manifest["databases"].items()}
        if len(sources) != len(SCHEMA):
            return ["defer properties until all databases exist"]
        for name, desired in SCHEMA.items():
            source_id = sources[name]
            source = self.client.request("GET", f"/data_sources/{source_id}")
            existing = source.get("properties", {})
            missing = {key: property_body(value, sources, inverse=INVERSE_RELATIONS.get((name, key)))
                       for key, value in desired.items() if key not in existing}
            # Existing properties are never silently changed or deleted.
            for key, value in desired.items():
                if key in existing and existing[key].get("type") != value.kind:
                    raise ValueError(f"Type conflict: {name}.{key}; review migration")
            if missing:
                changes.append(f"add {len(missing)} properties: {name}")
                if apply:
                    self.snapshot_source(name, source)
                    try:
                        self.client.request("PATCH", f"/data_sources/{source_id}", {"properties": missing})
                    except AmbiguousWrite:
                        current = self.client.request("GET", f"/data_sources/{source_id}")
                        if not all(key in current.get("properties", {}) for key in missing):
                            raise
        return changes

    def reconcile_views(self, *, apply: bool) -> list[str]:
        changes = []
        for database_name, ids in self.manifest["databases"].items():
            present = self.client.list_views(ids["database_id"])
            by_name: dict[str, list[dict]] = {}
            for view in present:
                by_name.setdefault(view.get("name", ""), []).append(view)
            for view in (v for v in VIEWS if v.database == database_name):
                matches = by_name.get(view.name, [])
                if len(matches) > 1:
                    raise ValueError(f"Duplicate view: {database_name}/{view.name}")
                if matches:
                    self.manifest["views"][f"{database_name}/{view.name}"] = matches[0]["id"]
                    continue
                changes.append(f"create view: {database_name}/{view.name}")
                if apply:
                    body = {"database_id": ids["database_id"],
                            "data_source_id": ids["data_source_id"],
                            "name": view.name, "type": "table"}
                    if view.filter:
                        body["filter"] = view.filter
                    if view.sorts:
                        body["sorts"] = list(view.sorts)
                    try:
                        result = self.client.request("POST", "/views", body)
                    except AmbiguousWrite:
                        matches = [x for x in self.client.list_views(ids["database_id"])
                                   if x.get("name") == view.name]
                        if len(matches) != 1:
                            raise
                        result = matches[0]
                    self.manifest["views"][f"{database_name}/{view.name}"] = result["id"]
                    self.save()
        self.save()
        return changes

    def run(self, *, apply: bool = False) -> list[str]:
        root = self.resolve_root(apply=apply)
        if not root:
            return plan_offline()
        changes = []
        changes += self.resolve_pages(root, apply=apply)
        changes += self.resolve_databases(root, apply=apply)
        changes += self.reconcile_properties(apply=apply)
        changes += self.reconcile_views(apply=apply)
        return changes


def load_manifest(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return {}
