import unittest

from gristcode.doc import Column, Table
from gristcode.render import grist_type, render, render_column, render_table


class GristTypeTest(unittest.TestCase):
    def test_a_plain_type_takes_no_argument(self):
        self.assertEqual(grist_type("Text"), "grist.Text()")

    def test_an_empty_type_becomes_any(self):
        self.assertEqual(grist_type(""), "grist.Any()")

    def test_a_reference_names_its_table(self):
        self.assertEqual(grist_type("Ref:People"), "grist.Reference('People')")

    def test_a_reference_list_names_its_table(self):
        self.assertEqual(grist_type("RefList:People"), "grist.ReferenceList('People')")

    def test_a_reverse_reference_carries_the_other_column(self):
        self.assertEqual(
            grist_type("Ref:People", "Orders"),
            "grist.Reference('People', reverse_of='Orders')",
        )

    def test_a_reverse_column_is_ignored_on_a_type_that_is_not_a_reference(self):
        self.assertEqual(grist_type("Text", "Orders"), "grist.Text()")

    def test_a_quote_in_the_argument_is_escaped(self):
        self.assertEqual(grist_type("Choice:it's"), "grist.Choice('it\\'s')")


class RenderColumnTest(unittest.TestCase):
    def test_a_data_column_is_one_assignment(self):
        column = Column("Name", "Text", False, "")
        self.assertEqual(render_column(column), ["  Name = grist.Text()"])

    def test_a_formula_column_is_a_function(self):
        column = Column("Greeting", "Text", True, 'return "Hi " + $Name')
        self.assertEqual(render_column(column), [
            "",
            "  @grist.formulaType(grist.Text())",
            "  def Greeting(rec, table):",
            '    return "Hi " + $Name',
        ])

    def test_an_untyped_formula_column_carries_no_decorator(self):
        column = Column("Anything", "Any", True, "1")
        self.assertEqual(render_column(column), [
            "",
            "  def Anything(rec, table):",
            "    1",
        ])

    def test_a_multi_line_formula_keeps_its_own_indentation(self):
        column = Column("Total", "Numeric", True, "x = 1\nif x:\n  return x\nreturn 0")
        self.assertEqual(render_column(column)[3:], [
            "    x = 1",
            "    if x:",
            "      return x",
            "    return 0",
        ])

    def test_an_empty_formula_body_becomes_pass(self):
        column = Column("Blank", "Any", True, "")
        self.assertEqual(render_column(column)[-1], "    pass")

    def test_a_data_column_with_a_trigger_formula_shows_it_as_a_comment(self):
        column = Column("Created", "DateTime", False, "NOW()")
        self.assertEqual(render_column(column), [
            "  # trigger formula:",
            "  #   NOW()",
            "  Created = grist.DateTime()",
        ])


class RenderTableTest(unittest.TestCase):
    def table(self, columns, summary=None):
        return Table("People", columns, summary_source=summary)

    def test_a_table_is_a_decorated_class(self):
        lines = render_table(self.table([Column("Name", "Text", False, "")]))
        self.assertEqual(lines[:2], ["@grist.UserTable", "class People:"])

    def test_an_empty_table_gets_a_pass(self):
        self.assertEqual(render_table(self.table([])), [
            "@grist.UserTable",
            "class People:",
            "  pass",
        ])

    def test_hidden_columns_are_dropped_by_default(self):
        columns = [Column("manualSort", "Int", False, ""), Column("Name", "Text", False, "")]
        lines = render_table(self.table(columns))
        self.assertEqual(lines, ["@grist.UserTable", "class People:", "  Name = grist.Text()"])

    def test_hidden_columns_come_back_on_request(self):
        columns = [Column("manualSort", "Int", False, ""), Column("Name", "Text", False, "")]
        lines = render_table(self.table(columns), include_hidden=True)
        self.assertIn("  manualSort = grist.Int()", lines)

    def test_a_summary_table_names_its_source(self):
        lines = render_table(self.table([], summary="Orders"))
        self.assertEqual(lines[2], "  _summarySourceTable = 'Orders'")


class RenderTest(unittest.TestCase):
    def test_the_header_is_two_comment_lines(self):
        text = render([])
        self.assertEqual(len(text.strip().splitlines()), 2)
        self.assertTrue(text.startswith("# Rendered by gristcode."))

    def test_the_header_can_be_dropped(self):
        self.assertEqual(render([], header=False), "")

    def test_tables_are_separated_by_a_blank_line(self):
        tables = [
            Table("A", [Column("x", "Text", False, "")]),
            Table("B", [Column("y", "Text", False, "")]),
        ]
        text = render(tables, header=False)
        self.assertEqual(text, (
            "@grist.UserTable\n"
            "class A:\n"
            "  x = grist.Text()\n"
            "\n\n"
            "@grist.UserTable\n"
            "class B:\n"
            "  y = grist.Text()\n"
        ))


if __name__ == "__main__":
    unittest.main()
