import os
import sqlite3
import tempfile
import unittest

import fixture
from gristcode.doc import DocumentError, read_tables


class ReadTablesTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, "doc.grist")
        fixture.simple_document(self.path)

    def tearDown(self):
        self.dir.cleanup()

    def test_tables_come_back_sorted_by_id(self):
        tables = read_tables(self.path)
        self.assertEqual(
            [t.table_id for t in tables],
            ["Orders", "Orders_summary_Customer", "People"],
        )

    def test_summary_table_points_at_its_source(self):
        summary = {t.table_id: t for t in read_tables(self.path)}["Orders_summary_Customer"]
        self.assertTrue(summary.is_summary)
        self.assertEqual(summary.summary_source, "Orders")

    def test_plain_table_is_not_a_summary(self):
        people = {t.table_id: t for t in read_tables(self.path)}["People"]
        self.assertFalse(people.is_summary)
        self.assertIsNone(people.summary_source)

    def test_data_columns_come_before_formula_columns(self):
        people = {t.table_id: t for t in read_tables(self.path)}["People"]
        self.assertEqual(
            [c.col_id for c in people.columns],
            ["manualSort", "Name", "Age", "Greeting"],
        )

    def test_helper_columns_are_flagged_hidden(self):
        by_table = {t.table_id: t for t in read_tables(self.path)}
        hidden = {c.col_id for c in by_table["People"].columns if c.is_hidden}
        self.assertEqual(hidden, {"manualSort"})
        hidden = {c.col_id for c in by_table["Orders"].columns if c.is_hidden}
        self.assertEqual(hidden, {"gristHelper_Display"})

    def test_formula_text_is_kept_verbatim(self):
        people = {t.table_id: t for t in read_tables(self.path)}["People"]
        greeting = [c for c in people.columns if c.col_id == "Greeting"][0]
        self.assertTrue(greeting.is_formula)
        self.assertEqual(greeting.formula, 'return "Hi " + $Name')

    def test_reverse_reference_is_resolved_to_a_column_id(self):
        path = os.path.join(self.dir.name, "reverse.grist")
        fixture.write_document(
            path,
            [(1, "People", 0), (2, "Orders", 0)],
            [
                (10, 1, 1.0, "Orders", "RefList:Orders", 0, "", 20),
                (20, 2, 1.0, "Customer", "Ref:People", 0, "", 10),
            ],
        )
        by_table = {t.table_id: t for t in read_tables(path)}
        self.assertEqual(by_table["People"].columns[0].reverse_col_id, "Customer")
        self.assertEqual(by_table["Orders"].columns[0].reverse_col_id, "Orders")

    def test_document_without_the_reverse_column_still_reads(self):
        path = os.path.join(self.dir.name, "old.grist")
        fixture.write_document(
            path,
            [(1, "People", 0)],
            [(10, 1, 1.0, "Name", "Text", 0, "", 0)],
            with_reverse_col=False,
        )
        tables = read_tables(path)
        self.assertEqual([c.col_id for c in tables[0].columns], ["Name"])
        self.assertIsNone(tables[0].columns[0].reverse_col_id)

    def test_a_sqlite_file_without_grist_metadata_is_refused(self):
        path = os.path.join(self.dir.name, "plain.sqlite")
        conn = sqlite3.connect(path)
        conn.execute("CREATE TABLE t (a INTEGER)")
        conn.commit()
        conn.close()
        with self.assertRaises(DocumentError):
            read_tables(path)

    def test_a_file_that_is_not_sqlite_is_refused(self):
        path = os.path.join(self.dir.name, "notes.txt")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("this is not a database")
        with self.assertRaises(DocumentError):
            read_tables(path)

    def test_a_path_holding_a_question_mark_still_opens_read_only(self):
        path = os.path.join(self.dir.name, "odd?name#1.grist")
        fixture.write_document(
            path,
            [(1, "People", 0)],
            [(10, 1, 1.0, "Name", "Text", 0, "", 0)],
        )
        before = os.stat(path)
        tables = read_tables(path)
        self.assertEqual([t.table_id for t in tables], ["People"])
        self.assertEqual(os.stat(path).st_mtime, before.st_mtime)

    def test_a_missing_file_is_refused(self):
        with self.assertRaises(DocumentError):
            read_tables(os.path.join(self.dir.name, "absent.grist"))


if __name__ == "__main__":
    unittest.main()
