"""Read the schema of a Grist document out of its SQLite file.

A .grist document is a SQLite database. The document's own structure lives in two metadata tables,
`_grist_Tables` and `_grist_Tables_column`, whose shape is defined upstream in
sandbox/grist/schema.py. Only those two tables are read here, and nothing is ever written.
"""

import os
import sqlite3
from urllib.parse import quote

TABLES_TABLE = "_grist_Tables"
COLUMNS_TABLE = "_grist_Tables_column"


class DocumentError(Exception):
    """The file is not a readable Grist document."""


class Column:
    """One column of one user table."""

    def __init__(self, col_id, col_type, is_formula, formula, label="", description="",
                 parent_pos=0.0, reverse_col_id=None):
        self.col_id = col_id
        self.col_type = col_type or "Any"
        self.is_formula = bool(is_formula)
        self.formula = formula or ""
        self.label = label or ""
        self.description = description or ""
        self.parent_pos = parent_pos or 0.0
        self.reverse_col_id = reverse_col_id or None

    @property
    def is_hidden(self):
        """True for the helper columns Grist maintains for itself, which no user typed."""
        return (
            self.col_id == "manualSort"
            or self.col_id.startswith("gristHelper_")
            or self.col_id.startswith("#")
        )

    def as_dict(self):
        return {
            "colId": self.col_id,
            "type": self.col_type,
            "isFormula": self.is_formula,
            "formula": self.formula,
            "label": self.label,
            "description": self.description,
            "reverseColId": self.reverse_col_id,
        }


class Table:
    """One user table of the document."""

    def __init__(self, table_id, columns, summary_source=None):
        self.table_id = table_id
        self.columns = columns
        self.summary_source = summary_source

    @property
    def is_summary(self):
        return self.summary_source is not None

    def as_dict(self):
        return {
            "tableId": self.table_id,
            "summarySourceTable": self.summary_source,
            "columns": [c.as_dict() for c in self.columns],
        }


def _column_names(conn, table_name):
    rows = conn.execute("PRAGMA table_info(%s)" % table_name).fetchall()
    return [row[1] for row in rows]


def _require_metadata(conn):
    names = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    missing = [t for t in (TABLES_TABLE, COLUMNS_TABLE) if t not in names]
    if missing:
        raise DocumentError(
            "this SQLite file carries no Grist document metadata (missing %s)"
            % ", ".join(missing)
        )


def _select(conn, table_name, wanted):
    """Select the wanted columns, tolerating the ones an older document does not carry."""
    present = _column_names(conn, table_name)
    used = [name for name in wanted if name in present]
    rows = conn.execute("SELECT %s FROM %s" % (", ".join(used), table_name)).fetchall()
    return [dict(zip(used, row)) for row in rows]


def read_tables(path):
    """Return the user tables of the document at `path`, ordered by table id.

    Columns are ordered the way the document orders them, data columns before formula columns.
    """
    # The path is percent encoded before it goes into the URI, so that a name holding `?` or `#`
    # cannot end the query string early and drop the read only mode.
    uri = "file:%s?mode=ro" % quote(os.path.abspath(path))
    try:
        conn = sqlite3.connect(uri, uri=True)
    except sqlite3.Error as exc:
        raise DocumentError("cannot open %s: %s" % (path, exc))
    try:
        try:
            _require_metadata(conn)
            table_rows = _select(conn, TABLES_TABLE, ["id", "tableId", "summarySourceTable"])
            column_rows = _select(conn, COLUMNS_TABLE, [
                "id", "parentId", "parentPos", "colId", "type", "isFormula", "formula",
                "label", "description", "reverseCol",
            ])
        except sqlite3.DatabaseError as exc:
            raise DocumentError("cannot read %s: %s" % (path, exc))
    finally:
        conn.close()

    table_id_by_ref = {row["id"]: row["tableId"] for row in table_rows}
    col_id_by_ref = {row["id"]: row.get("colId") for row in column_rows}

    by_parent = {}
    for row in column_rows:
        column = Column(
            col_id=row.get("colId") or "",
            col_type=row.get("type"),
            is_formula=row.get("isFormula"),
            formula=row.get("formula"),
            label=row.get("label"),
            description=row.get("description"),
            parent_pos=row.get("parentPos"),
            reverse_col_id=col_id_by_ref.get(row.get("reverseCol")),
        )
        by_parent.setdefault(row.get("parentId"), []).append(column)

    tables = []
    for row in table_rows:
        columns = by_parent.get(row["id"], [])
        columns.sort(key=lambda c: (c.is_formula, c.parent_pos, c.col_id))
        tables.append(Table(
            table_id=row["tableId"],
            columns=columns,
            summary_source=table_id_by_ref.get(row.get("summarySourceTable")),
        ))
    tables.sort(key=lambda t: t.table_id)
    return tables
