"""Notion connector DDL for the approved property map."""

from __future__ import annotations

from .definitions import INVERSE_RELATIONS, SCHEMA, Property


def sql_type(prop: Property, sources: dict[str, str] | None = None) -> str:
    kinds = {"title": "TITLE", "rich_text": "RICH_TEXT", "date": "DATE",
             "checkbox": "CHECKBOX", "number": "NUMBER",
             "created_time": "CREATED_TIME", "status": "STATUS"}
    if prop.kind in kinds:
        return kinds[prop.kind]
    if prop.kind in ("select", "multi_select"):
        options = ", ".join(f"'{value}':gray" for value in prop.options)
        return f"{prop.kind.upper()}({options})"
    if prop.kind == "formula":
        if not prop.expression:
            raise ValueError("Formula expression is empty")
        return "FORMULA('" + prop.expression.replace("'", "''") + "')"
    if prop.kind == "relation":
        if not sources or prop.target not in sources:
            raise ValueError(f"Missing data source ID for {prop.target}")
        return f"RELATION('{sources[prop.target]}')"
    raise ValueError(prop.kind)


def create_table(name: str) -> str:
    fields = SCHEMA[name]
    columns = [f'"{column}" {sql_type(prop)}' for column, prop in fields.items()
               if prop.kind != "relation"]
    return "CREATE TABLE (" + ", ".join(columns) + ")"


def relation_updates(name: str, sources: dict[str, str]) -> str:
    fields = SCHEMA[name]
    statements = []
    for column, prop in fields.items():
        if prop.kind != "relation":
            continue
        inverse = INVERSE_RELATIONS.get((name, column))
        if inverse:
            kind = f"RELATION('{sources[prop.target]}', DUAL '{inverse}' '{inverse.lower().replace(' ', '_')}')"
        else:
            kind = sql_type(prop, sources)
        statements.append(f'ADD COLUMN "{column}" {kind}')
    return "; ".join(statements)
