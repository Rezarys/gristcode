"""Build a small SQLite file shaped like a Grist document, for the tests only.

No real document is used anywhere in this suite. The two metadata tables are created with the
columns the upstream schema gives them, and filled by hand.
"""

import sqlite3

TABLES_DDL = """
CREATE TABLE _grist_Tables (
  id INTEGER PRIMARY KEY,
  tableId TEXT,
  primaryViewId INTEGER,
  summarySourceTable INTEGER,
  onDemand INTEGER
)
"""

COLUMNS_DDL = """
CREATE TABLE _grist_Tables_column (
  id INTEGER PRIMARY KEY,
  parentId INTEGER,
  parentPos REAL,
  colId TEXT,
  type TEXT,
  widgetOptions TEXT,
  isFormula INTEGER,
  formula TEXT,
  label TEXT,
  description TEXT,
  reverseCol INTEGER
)
"""


def write_document(path, tables, columns, with_reverse_col=True):
    """Write a document file.

    `tables` is a list of (id, tableId, summarySourceTable).
    `columns` is a list of (id, parentId, parentPos, colId, type, isFormula, formula, reverseCol).
    """
    conn = sqlite3.connect(str(path))
    try:
        conn.execute(TABLES_DDL)
        columns_ddl = COLUMNS_DDL
        if not with_reverse_col:
            columns_ddl = columns_ddl.replace(",\n  reverseCol INTEGER", "")
        conn.execute(columns_ddl)
        conn.executemany(
            "INSERT INTO _grist_Tables (id, tableId, summarySourceTable) VALUES (?, ?, ?)",
            tables,
        )
        for row in columns:
            col_id, parent_id, pos, name, col_type, is_formula, formula, reverse = row
            if with_reverse_col:
                conn.execute(
                    "INSERT INTO _grist_Tables_column "
                    "(id, parentId, parentPos, colId, type, isFormula, formula, reverseCol) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (col_id, parent_id, pos, name, col_type, is_formula, formula, reverse),
                )
            else:
                conn.execute(
                    "INSERT INTO _grist_Tables_column "
                    "(id, parentId, parentPos, colId, type, isFormula, formula) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (col_id, parent_id, pos, name, col_type, is_formula, formula),
                )
        conn.commit()
    finally:
        conn.close()


def simple_document(path):
    """A document with two user tables, one summary table, and one helper column."""
    tables = [
        (1, "People", 0),
        (2, "Orders", 0),
        (3, "Orders_summary_Customer", 2),
    ]
    columns = [
        (10, 1, 1.0, "manualSort", "ManualSortPos", 0, "", 0),
        (11, 1, 2.0, "Name", "Text", 0, "", 0),
        (12, 1, 3.0, "Age", "Int", 0, "", 0),
        (13, 1, 4.0, "Greeting", "Text", 1, 'return "Hi " + $Name', 0),
        (20, 2, 1.0, "Customer", "Ref:People", 0, "", 0),
        (21, 2, 2.0, "Amount", "Numeric", 0, "", 0),
        (22, 2, 3.0, "Placed", "DateTime:UTC", 0, "NOW()", 0),
        (23, 2, 4.0, "gristHelper_Display", "Any", 1, "$Customer.Name", 0),
        (30, 3, 1.0, "count", "Int", 1, "len($group)", 0),
    ]
    write_document(path, tables, columns)
    return path
