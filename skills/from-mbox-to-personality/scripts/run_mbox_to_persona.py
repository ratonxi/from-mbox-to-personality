#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys
from pathlib import Path


def run(args):
    print("+", " ".join(args), flush=True)
    repo_root = Path(__file__).resolve().parents[3]
    env = os.environ.copy()
    src = str(repo_root / "src")
    env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")
    subprocess.run(args, check=True, env=env)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mbox", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--target-email", action="append", default=[])
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--progress-every", type=int, default=5000)
    parser.add_argument("--no-redact", action="store_true")
    args = parser.parse_args()

    out = Path(args.out)
    scan_cmd = [
        sys.executable, "-m", "mbox_to_persona.cli", "scan",
        "--mbox", args.mbox,
        "--out", str(out),
    ]
    for email in args.target_email:
        scan_cmd.extend(["--target-email", email])
    if args.limit:
        scan_cmd.extend(["--limit", str(args.limit)])
    if args.progress_every:
        scan_cmd.extend(["--progress-every", str(args.progress_every)])
    if args.no_redact:
        scan_cmd.append("--no-redact")

    run(scan_cmd)
    run([sys.executable, "-m", "mbox_to_persona.cli", "persona", "--input", str(out / "index.csv"), "--out", str(out / "persona")])
    run([sys.executable, "-m", "mbox_to_persona.cli", "profile", "--input", str(out / "index.csv"), "--out", str(out / "profile")])
    run([
        sys.executable, "-m", "mbox_to_persona.cli", "export-prompt",
        "--persona", str(out / "persona" / "persona.json"),
        "--out", str(out / "persona" / "style_prompt_export.md"),
    ])
    run([
        sys.executable, "-m", "mbox_to_persona.cli", "graphs",
        "--input", str(out / "index.csv"),
        "--persona", str(out / "persona" / "persona.json"),
        "--out", str(out / "graphs"),
    ])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
