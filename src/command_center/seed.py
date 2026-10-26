"""Approved starter records only; never invent ATLAS phases or success criteria."""

from __future__ import annotations

from .definitions import AREA_SEEDS
from .notion import AmbiguousWrite, NotionClient, prop_text, rich_text


def find_unique(client: NotionClient, source_id: str, name: str) -> dict | None:
    found = [row for row in client.query_all(source_id) if prop_text(row, "Name") == name]
    if len(found) > 1:
        raise ValueError(f"Duplicate record: {name}")
    return found[0] if found else None


def create_once(client: NotionClient, source_id: str, name: str, properties: dict) -> dict:
    found = find_unique(client, source_id, name)
    if found:
        return found
    payload = {"parent": {"type": "data_source_id", "data_source_id": source_id},
               "properties": {"Name": {"title": rich_text(name)}, **properties}}
    try:
        return client.request("POST", "/pages", payload)
    except AmbiguousWrite:
        found = find_unique(client, source_id, name)
        if not found:
            raise
        return found


def seed_approved(client: NotionClient, databases: dict) -> dict:
    source = lambda name: databases[name]["data_source_id"]
    areas = {}
    for name in AREA_SEEDS:
        areas[name] = create_once(client, source("Areas"), name,
                                  {"State": {"select": {"name": "Active"}}})
    area_id = areas["Tech Career"]["id"]
    goal = create_once(client, source("Goals"), "Gain skills and broaden personal portfolio", {
        "Status": {"status": {"name": "Planned"}},
        "Primary Area": {"relation": [{"id": area_id}]},
    })
    project = create_once(client, source("Projects"), "ATLAS", {
        "Status": {"status": {"name": "Planned"}},
        "Project kind": {"select": {"name": "Project"}},
        "Primary Area": {"relation": [{"id": area_id}]},
        "Goal": {"relation": [{"id": goal["id"]}]},
    })
    return {"areas": {name: row["id"] for name, row in areas.items()},
            "goal": goal["id"], "project": project["id"]}
