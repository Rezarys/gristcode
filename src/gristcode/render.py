"""Turn the tables of a document into Python source text.

The shape follows the class-per-table rendering the Grist sandbox uses (upstream
sandbox/grist/gencode.py). Formula bodies are printed exactly as the document stores them, which
is how they were typed; the sandbox rewrites them before running them, and that rewriting is not
done here.
"""

INDENT = "  "

HEADER = (
    "# Rendered by gristcode. Formula bodies are shown exactly as stored in the document,\n"
    "# so this text is meant to be read and compared, not executed.\n"
)


def grist_type(col_type, reverse_col_id=None):
    """Return the Grist type expression for a column type string, e.g. `grist.Reference('People')`."""
    head, _, tail = (col_type or "").partition(":")
    name = head.strip() or "Any"
    if name == "Ref":
        name = "Reference"
    elif name == "RefList":
        name = "ReferenceList"
    args = []
    tail = tail.strip().replace("'", "\\'")
    if tail:
        args.append("'%s'" % tail)
    if reverse_col_id and name in ("Reference", "ReferenceList"):
        args.append("reverse_of=%r" % reverse_col_id)
    return "grist.%s(%s)" % (name, ", ".join(args))


def _block(text, indent):
    """Indent a formula body, giving `pass` when the document holds no text at all."""
    lines = (text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        return [indent + "pass"]
    return [(indent + line).rstrip() for line in lines]


def render_column(column, indent=INDENT):
    """Return the lines rendering one column."""
    type_expr = grist_type(column.col_type, column.reverse_col_id)
    if column.is_formula:
        lines = [""]
        if column.col_type != "Any":
            lines.append("%s@grist.formulaType(%s)" % (indent, type_expr))
        lines.append("%sdef %s(rec, table):" % (indent, column.col_id))
        lines.extend(_block(column.formula, indent + INDENT))
        return lines
    lines = []
    if column.formula:
        lines.append("%s# trigger formula:" % indent)
        lines.extend("%s#   %s" % (indent, line) for line in _block(column.formula, ""))
    lines.append("%s%s = %s" % (indent, column.col_id, type_expr))
    return lines


def render_table(table, include_hidden=False):
    """Return the lines rendering one table as a class."""
    lines = ["@grist.UserTable", "class %s:" % table.table_id]
    if table.is_summary:
        lines.append("%s_summarySourceTable = %r" % (INDENT, table.summary_source))
    columns = [c for c in table.columns if include_hidden or not c.is_hidden]
    for column in columns:
        lines.extend(render_column(column))
    if len(lines) == 2:
        lines.append(INDENT + "pass")
    return lines


def render(tables, include_hidden=False, header=True):
    """Return the whole document as one block of Python source text."""
    parts = [HEADER] if header else []
    for table in tables:
        parts.append("\n".join(render_table(table, include_hidden=include_hidden)) + "\n")
    return "\n\n".join(parts)
