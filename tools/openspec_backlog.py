import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from openspec_change_meta import CHANGES_DIR, ChangeMeta, list_non_archived_change_dirs, load_meta

STATUS_ORDER = {"active": 0, "queued": 1, "blocked": 2, "superseded": 3}
ASSUMPTION_ORDER = {"valid": 0, "needs-review": 1, "invalid": 2}
PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2}
EVIDENCE_ORDER = {
    "tests": 0,
    "host-validation": 1,
    "cli-transcript": 2,
    "manual-check": 3,
}


@dataclass(frozen=True)
class ChangeRecord:
    name: str
    path: Path
    meta: ChangeMeta


def load_change_records(changes_dir: Optional[Path] = None) -> list[ChangeRecord]:
    changes_dir = CHANGES_DIR if changes_dir is None else changes_dir
    records = []
    for change_dir in list_non_archived_change_dirs(changes_dir):
        meta_path = change_dir / "meta.yaml"
        if not meta_path.exists():
            continue
        records.append(ChangeRecord(name=change_dir.name, path=change_dir, meta=load_meta(meta_path)))
    return records


def derive_unlock_counts(records: list[ChangeRecord]) -> dict[str, int]:
    counts = {record.name: 0 for record in records}
    for record in records:
        for dependency in record.meta.blocked_by:
            if dependency in counts:
                counts[dependency] += 1
    return counts


def filter_records(
    records: list[ChangeRecord],
    *,
    status: Optional[str] = None,
    change_type: Optional[str] = None,
    priority: Optional[str] = None,
    evidence: Optional[str] = None,
    assumption_state: Optional[str] = None,
    actionable_only: bool = False,
    backlog_only: bool = False,
) -> list[ChangeRecord]:
    filtered = []
    for record in records:
        meta = record.meta
        if backlog_only and meta.status != "queued":
            continue
        if actionable_only and meta.status not in ("active", "queued"):
            continue
        if actionable_only and meta.assumption_state == "invalid":
            continue
        if status and meta.status != status:
            continue
        if change_type and meta.change_type != change_type:
            continue
        if priority and meta.priority != priority:
            continue
        if evidence and meta.evidence != evidence:
            continue
        if assumption_state and meta.assumption_state != assumption_state:
            continue
        filtered.append(record)
    return filtered


def rank_records(records: list[ChangeRecord]) -> list[tuple[ChangeRecord, int, list[str]]]:
    unlock_counts = derive_unlock_counts(records)
    ranked = []
    for record in records:
        meta = record.meta
        reasons = [
            f"status={meta.status}",
            f"assumption_state={meta.assumption_state}",
            f"priority={meta.priority}",
            f"unlock_count={unlock_counts.get(record.name, 0)}",
            f"evidence={meta.evidence}",
            f"updated_at={meta.updated_at}",
        ]
        key = (
            STATUS_ORDER[meta.status],
            ASSUMPTION_ORDER[meta.assumption_state],
            PRIORITY_ORDER[meta.priority],
            -unlock_counts.get(record.name, 0),
            EVIDENCE_ORDER[meta.evidence],
            -int(meta.updated_at.replace("-", "")),
            record.name,
        )
        ranked.append((record, unlock_counts.get(record.name, 0), reasons, key))
    ranked.sort(key=lambda item: item[3])
    return [(record, unlock_count, reasons) for record, unlock_count, reasons, _ in ranked]


def build_parser():
    parser = argparse.ArgumentParser(
        description="Filter and rank non-archived OpenSpec changes from repository-owned metadata."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List matching changes.")
    next_parser = subparsers.add_parser("next", help="Recommend the next actionable change.")

    for subparser in (list_parser, next_parser):
        subparser.add_argument("--status", help="Filter by status.")
        subparser.add_argument("--type", dest="change_type", help="Filter by change type.")
        subparser.add_argument("--priority", help="Filter by priority.")
        subparser.add_argument("--evidence", help="Filter by evidence target.")
        subparser.add_argument("--assumption-state", help="Filter by assumption state.")
        subparser.add_argument(
            "--backlog",
            action="store_true",
            help="Shortcut for backlog view, equivalent to status=queued.",
        )
        subparser.add_argument(
            "--json",
            action="store_true",
            help="Emit JSON instead of human-readable text.",
        )

    return parser


def _collect_records(args) -> list[tuple[ChangeRecord, int, list[str]]]:
    records = load_change_records()
    filtered = filter_records(
        records,
        status=args.status,
        change_type=args.change_type,
        priority=args.priority,
        evidence=args.evidence,
        assumption_state=args.assumption_state,
        actionable_only=args.command == "next",
        backlog_only=args.backlog,
    )
    return rank_records(filtered)


def _serialize(rankings: list[tuple[ChangeRecord, int, list[str]]]) -> list[dict[str, object]]:
    payload = []
    for record, unlock_count, reasons in rankings:
        payload.append(
            {
                "name": record.name,
                "path": str(record.path),
                "meta": {
                    "status": record.meta.status,
                    "change_type": record.meta.change_type,
                    "priority": record.meta.priority,
                    "blocked_by": list(record.meta.blocked_by),
                    "assumption_state": record.meta.assumption_state,
                    "evidence": record.meta.evidence,
                    "updated_at": record.meta.updated_at,
                },
                "unlock_count": unlock_count,
                "reasons": reasons,
            }
        )
    return payload


def _print_human_list(rankings: list[tuple[ChangeRecord, int, list[str]]], command: str):
    if not rankings:
        print("No matching changes.")
        return

    if command == "next":
        record, _, reasons = rankings[0]
        print(f"Recommended next change: {record.name}")
        for reason in reasons:
            print(f"- {reason}")
        return

    for record, _, reasons in rankings:
        print(record.name)
        for reason in reasons:
            print(f"- {reason}")


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.backlog and args.status and args.status != "queued":
        parser.error("--backlog is equivalent to --status queued and cannot be combined with a different status.")
    if args.backlog:
        args.status = "queued"

    rankings = _collect_records(args)
    if args.json:
        print(json.dumps(_serialize(rankings), ensure_ascii=False, indent=2))
    else:
        _print_human_list(rankings, args.command)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
