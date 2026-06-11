import argparse
import json
from pathlib import Path

from .export import export_prompt
from .graphs import generate_graphs
from .ingest import scan_mbox
from .persona import generate_persona
from .psych_profile import generate_profile


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="mbox-to-persona")
    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="Scan a Gmail MBOX and create local indexes.")
    scan.add_argument("--mbox", required=True)
    scan.add_argument("--out", required=True)
    scan.add_argument("--target-email", action="append", default=[])
    scan.add_argument("--limit", type=int, default=0)
    scan.add_argument("--no-redact", action="store_true")
    scan.add_argument("--progress-every", type=int, default=5000)

    persona = sub.add_parser("persona", help="Generate writing persona from index.csv.")
    persona.add_argument("--input", required=True)
    persona.add_argument("--out", required=True)

    profile = sub.add_parser("profile", help="Generate non-clinical communication profile.")
    profile.add_argument("--input", required=True)
    profile.add_argument("--out", required=True)

    exp = sub.add_parser("export-prompt", help="Export a pasteable persona prompt.")
    exp.add_argument("--persona", required=True)
    exp.add_argument("--out", required=True)

    graphs = sub.add_parser("graphs", help="Generate persona graphs such as the 0-10 radar chart.")
    graphs.add_argument("--input", required=True)
    graphs.add_argument("--out", required=True)
    graphs.add_argument("--persona")

    args = parser.parse_args(argv)

    if args.command == "scan":
        report = scan_mbox(
            mbox=Path(args.mbox),
            out=Path(args.out),
            target_emails=args.target_email,
            limit=args.limit,
            redact=not args.no_redact,
            progress_every=args.progress_every,
        )
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0
    if args.command == "persona":
        result = generate_persona(Path(args.input), Path(args.out))
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    if args.command == "profile":
        result = generate_profile(Path(args.input), Path(args.out))
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    if args.command == "export-prompt":
        export_prompt(Path(args.persona), Path(args.out))
        print(str(Path(args.out)))
        return 0
    if args.command == "graphs":
        result = generate_graphs(Path(args.input), Path(args.out), Path(args.persona) if args.persona else None)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
