import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

import fixture
from gristcode.cli import main

# Kept in step with the sample printed in README.md, so that the README cannot drift from the tool.
README_SAMPLE = '''\
# Rendered by gristcode. Formula bodies are shown exactly as stored in the document,
# so this text is meant to be read and compared, not executed.


@grist.UserTable
class Orders:
  Customer = grist.Reference('People')
  Amount = grist.Numeric()
  # trigger formula:
  #   NOW()
  Placed = grist.DateTime('UTC')


@grist.UserTable
class People:
  Name = grist.Text()
  Age = grist.Int()

  @grist.formulaType(grist.Text())
  def Greeting(rec, table):
    return "Hi " + $Name
'''


class CliTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, "doc.grist")
        fixture.simple_document(self.path)

    def tearDown(self):
        self.dir.cleanup()

    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_a_document_renders_its_user_tables(self):
        code, out, _ = self.run_cli(self.path)
        self.assertEqual(code, 0)
        self.assertIn("class People:", out)
        self.assertIn("class Orders:", out)

    def test_summary_tables_are_left_out_by_default(self):
        _, out, _ = self.run_cli(self.path)
        self.assertNotIn("Orders_summary_Customer", out)

    def test_summary_tables_come_back_on_request(self):
        _, out, _ = self.run_cli(self.path, "--include-summary")
        self.assertIn("class Orders_summary_Customer:", out)
        self.assertIn("_summarySourceTable = 'Orders'", out)

    def test_helper_columns_are_left_out_by_default(self):
        _, out, _ = self.run_cli(self.path)
        self.assertNotIn("manualSort", out)
        self.assertNotIn("gristHelper_Display", out)

    def test_helper_columns_come_back_on_request(self):
        _, out, _ = self.run_cli(self.path, "--include-hidden")
        self.assertIn("manualSort", out)

    def test_one_table_can_be_asked_for(self):
        _, out, _ = self.run_cli(self.path, "--table", "People")
        self.assertIn("class People:", out)
        self.assertNotIn("class Orders:", out)

    def test_two_tables_can_be_asked_for(self):
        _, out, _ = self.run_cli(self.path, "-t", "People", "-t", "Orders")
        self.assertIn("class People:", out)
        self.assertIn("class Orders:", out)

    def test_an_unknown_table_is_an_error(self):
        code, _, err = self.run_cli(self.path, "--table", "Nope")
        self.assertEqual(code, 2)
        self.assertIn("no such table: Nope", err)

    def test_a_summary_table_can_be_asked_for_by_name(self):
        _, out, _ = self.run_cli(self.path, "--table", "Orders_summary_Customer")
        self.assertIn("class Orders_summary_Customer:", out)

    def test_the_header_can_be_dropped(self):
        _, out, _ = self.run_cli(self.path, "--no-header")
        self.assertTrue(out.startswith("@grist.UserTable"))

    def test_json_output_is_a_list_of_tables(self):
        code, out, _ = self.run_cli(self.path, "--json")
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(
            [entry["tableId"] for entry in payload],
            ["Orders", "People"],
        )

    def test_json_output_drops_helper_columns_by_default(self):
        _, out, _ = self.run_cli(self.path, "--json")
        payload = {entry["tableId"]: entry for entry in json.loads(out)}
        self.assertEqual(
            [c["colId"] for c in payload["Orders"]["columns"]],
            ["Customer", "Amount", "Placed"],
        )

    def test_json_output_keeps_the_formula_text(self):
        _, out, _ = self.run_cli(self.path, "--json")
        payload = {entry["tableId"]: entry for entry in json.loads(out)}
        greeting = [
            c for c in payload["People"]["columns"] if c["colId"] == "Greeting"
        ][0]
        self.assertEqual(greeting["formula"], 'return "Hi " + $Name')

    def test_an_unreadable_document_exits_with_two(self):
        code, _, err = self.run_cli(os.path.join(self.dir.name, "absent.grist"))
        self.assertEqual(code, 2)
        self.assertIn("gristcode:", err)

    def test_the_version_is_printed(self):
        out = io.StringIO()
        with redirect_stdout(out):
            with self.assertRaises(SystemExit) as caught:
                main(["--version"])
        self.assertEqual(caught.exception.code, 0)
        self.assertIn("gristcode", out.getvalue())

    def test_the_whole_rendering_is_the_one_shown_in_the_readme(self):
        _, out, _ = self.run_cli(self.path)
        self.assertEqual(out, README_SAMPLE)

    def test_the_document_file_is_not_modified(self):
        before = os.stat(self.path)
        self.run_cli(self.path)
        after = os.stat(self.path)
        self.assertEqual(before.st_size, after.st_size)
        self.assertEqual(before.st_mtime, after.st_mtime)


if __name__ == "__main__":
    unittest.main()
