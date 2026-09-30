# gristcode

```
pip install gristcode
```

Not affiliated with Grist Labs. "Grist" is used here only to say which file this tool reads.

Print a Grist document as readable Python source, offline, straight from the `.grist` file, so you can read it in your editor, diff it, and commit it.

Grist already shows a rendering of your document as Python in its Code view panel, but there is no way to get that text out of the browser other than selecting the page, pasting it somewhere, and deleting everything that came along with it. `gristcode` gives you the same shape of text on standard output, from the file, with nothing to trim.

## Use

```
gristcode mydoc.grist
gristcode mydoc.grist --table People --table Orders
gristcode mydoc.grist --json
```

A `.grist` file is what the Download button gives you in the document menu, and it is also the file a self-hosted instance keeps on disk. The document is opened read only and is never written to.

Output on a small document with two tables:

```
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
```

## Options

- `-t NAME`, `--table NAME`: render only this table, and repeat the option for several tables. Naming a summary table explicitly works too.
- `--include-summary`: also render the summary tables Grist builds from your own tables. They are left out by default.
- `--include-hidden`: also render the helper columns Grist maintains for itself. The rule used here is that a column is a helper when its identifier is `manualSort`, or starts with `gristHelper_`, or starts with `#`.
- `--no-header`: drop the two header comment lines, which is handy when the output goes into version control.
- `--json`: print the schema as JSON instead of Python, with one entry per table and the column identifier, type, formula, label and description of each column.
- `--version`: print the version and exit.

Exit code is 0 on success and 2 when the file cannot be read as a Grist document or when a table named with `--table` does not exist.

## What this is not

The Code view panel inside Grist shows formula bodies **after** the sandbox has rewritten them, which is where `$field` becomes `rec.field` and a `return` gets inserted. `gristcode` does not do that rewriting: it prints each formula exactly as the document stores it, which is how you typed it. The output is therefore made to be read and compared, not executed, and the sample above shows `$Name` for that reason.

Only the two metadata tables `_grist_Tables` and `_grist_Tables_column` are read. Your data rows, your attachments and your access rules are never opened and never printed.

## Honest limits

This tool has never been run against a real Grist document. It is tested against small SQLite files written by its own test suite, shaped after the document metadata schema published in the Grist source tree. If you run it on a real document and something comes out wrong, please open an issue and paste what you got.

The shape of the output follows the schema as of Grist schema version 46. A document saved by a much older or much newer version may carry columns this tool does not know about, and those are ignored rather than guessed at.

## Install from source

```
git clone https://github.com/Rezarys/gristcode
pip install ./gristcode
```

Python 3.9 or newer. No dependencies outside the standard library.

Tests, once the package is installed:

```
python -m unittest discover -s tests -t tests
```

## Background

Built after a request on the Grist issue tracker for an easier way to get the document as code out of the Code view panel: https://github.com/gristlabs/grist-core/issues/2574

Built with AI assistance, reviewed and tested by me.

## License

MIT. Younes Z.
