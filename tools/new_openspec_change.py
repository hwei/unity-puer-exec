import argparse
import subprocess
from pathlib import Path

from openspec_change_meta import CHANGES_DIR, ensure_meta_file


def build_parser():
    parser = argparse.ArgumentParser(
        description="Create an OpenSpec change and seed repository-owned meta.yaml."
    )
    parser.add_argument("name", help="Kebab-case change name.")
    parser.add_argument(
        "--status",
        default=None,
        help="Optional explicit exception disposition such as blocked or superseded.",
    )
    parser.add_argument("--type", dest="change_type", default="spike", help="Initial change type.")
    parser.add_argument("--priority", default="P2", help="Initial change priority.")
    parser.add_argument(
        "--assumption-state",
        default="valid",
        help="Initial assumption state.",
    )
    parser.add_argument("--evidence", default="manual-check", help="Initial evidence target.")
    return parser


def create_change(change_name: str):
    subprocess.run(["openspec", "new", "change", change_name], check=True)


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    create_change(args.name)

    change_dir = CHANGES_DIR / args.name
    meta_path = ensure_meta_file(
        change_dir,
        defaults={
            "change_type": args.change_type,
            "priority": args.priority,
            "assumption_state": args.assumption_state,
            "evidence": args.evidence,
            **({"status": args.status} if args.status is not None else {}),
        },
    )

    print(str(Path(meta_path).resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
