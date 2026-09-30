"""Command line entry point."""

import argparse
import json
import sys

from . import __version__
from .doc import DocumentError, read_tables
from .render import render


def build_parser():
    parser = argparse.ArgumentParser(
        prog="gristcode",
        description="Render a Grist document as readable Python source, offline, "
                    "from its .grist file. The document is only ever read.",
    )
    parser.add_argument("document", help="path to a .grist file")
    parser.add_argument(
        "-t", "--table", action="append", default=[], metavar="NAME",
        help="only this table; repeat the option for several tables",
    )
    parser.add_argument(
        "--include-summary", action="store_true",
        help="also render the summary tables Grist builds from your own tables",
    )
    parser.add_argument(
        "--include-hidden", action="store_true",
        help="also render the helper columns Grist maintains for itself",
    )
    parser.add_argument("--no-header", action="store_true", help="drop the two header comments")
    parser.add_argument("--json", action="store_true", help="print the schema as JSON instead")
    parser.add_argument("--version", action="version", version="gristcode " + __version__)
    return parser


def select(tables, wanted, include_summary):
    if wanted:
        names = set(wanted)
        return [t for t in tables if t.table_id in names]
    return [t for t in tables if include_summary or not t.is_summary]


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        tables = read_tables(args.document)
    except DocumentError as exc:
        sys.stderr.write("gristcode: %s\n" % exc)
        return 2

    chosen = select(tables, args.table, args.include_summary)
    if args.table:
        missing = sorted(set(args.table) - {t.table_id for t in tables})
        if missing:
            sys.stderr.write("gristcode: no such table: %s\n" % ", ".join(missing))
            return 2

    if args.json:
        payload = []
        for table in chosen:
            entry = table.as_dict()
            if not args.include_hidden:
                entry["columns"] = [
                    c.as_dict() for c in table.columns if not c.is_hidden
                ]
            payload.append(entry)
        sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        return 0

    sys.stdout.write(render(
        chosen,
        include_hidden=args.include_hidden,
        header=not args.no_header,
    ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
