import argparse
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from openspec_change_meta import ARCHIVE_DIR, CHANGES_DIR, REPO_ROOT, ChangeMeta, list_non_archived_change_dirs, load_meta

DERIVED_STATUS_ORDER = {"eligible": 0, "blocked": 1, "inconsistent": 2, "superseded": 3}
ASSUMPTION_ORDER = {"valid": 0, "needs-review": 1, "invalid": 2}
PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2}
EVIDENCE_ORDER = {
    "tests": 0,
    "host-validation": 1,
    "cli-transcript": 2,
    "manual-check": 3,
}
ARCHIVE_NAME_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}-(.+)$")


@dataclass(frozen=True)
class ChangeRecord:
    name: str
    path: Path
    meta: ChangeMeta


@dataclass(frozen=True)
class EvaluatedRecord:
    record: ChangeRecord
    unlock_count: int
    derived_status: str
    eligible: bool
    unresolved_dependencies: tuple[str, ...]
    missing_dependencies: tuple[str, ...]
    diagnostics: tuple[str, ...]
    git_commit_distance: Optional[int]
    reasons: tuple[str, ...]


def load_change_records(changes_dir: Optional[Path] = None) -> list[ChangeRecord]:
    changes_dir = CHANGES_DIR if changes_dir is None else changes_dir
    records = []
    for change_dir in list_non_archived_change_dirs(changes_dir):
        meta_path = change_dir / "meta.yaml"
        if not meta_path.exists():
            continue
        records.append(ChangeRecord(name=change_dir.name, path=change_dir, meta=load_meta(meta_path)))
    return records


def load_archived_change_names(archive_dir: Optional[Path] = None) -> set[str]:
    archive_dir = ARCHIVE_DIR if archive_dir is None else archive_dir
    if not archive_dir.exists():
        return set()

    names = set()
    for path in archive_dir.iterdir():
        if not path.is_dir():
            continue
        match = ARCHIVE_NAME_PATTERN.match(path.name)
        names.add(match.group(1) if match else path.name)
    return names


def derive_unlock_counts(records: list[ChangeRecord]) -> dict[str, int]:
    counts = {record.name: 0 for record in records}
    for record in records:
        for dependency in record.meta.blocked_by:
            if dependency in counts:
                counts[dependency] += 1
    return counts


def get_git_commit_distance(change_path: Path, repo_root: Path = REPO_ROOT) -> Optional[int]:
    relative_path = change_path.relative_to(repo_root)
    last_commit = subprocess.run(
        ["git", "log", "-n", "1", "--format=%H", "--", str(relative_path)],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if last_commit.returncode != 0:
        return None

    commit_hash = last_commit.stdout.strip()
    if not commit_hash:
        return None

    distance = subprocess.run(
        ["git", "rev-list", "--count", f"{commit_hash}..HEAD"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if distance.returncode != 0:
        return None

    try:
        return int(distance.stdout.strip())
    except ValueError:
        return None


def evaluate_records(
    records: list[ChangeRecord],
    *,
    archive_dir: Optional[Path] = None,
    repo_root: Path = REPO_ROOT,
) -> list[EvaluatedRecord]:
    archived_names = load_archived_change_names(archive_dir)
    active_names = {record.name for record in records}
    unlock_counts = derive_unlock_counts(records)
    evaluated = []

    for record in records:
        unresolved_dependencies = []
        missing_dependencies = []
        for dependency in record.meta.blocked_by:
            if dependency in archived_names:
                continue
            if dependency in active_names:
                unresolved_dependencies.append(dependency)
                continue
            missing_dependencies.append(dependency)

        diagnostics = []
        derived_status = "eligible"
        eligible = True
        if record.meta.status == "superseded":
            derived_status = "superseded"
            eligible = False
            diagnostics.append("superseded")
        elif missing_dependencies:
            derived_status = "inconsistent"
            eligible = False
            diagnostics.append("missing_dependency")
        elif unresolved_dependencies or record.meta.assumption_state == "invalid":
            derived_status = "blocked"
            eligible = False
            if unresolved_dependencies:
                diagnostics.append("unresolved_dependency")
            if record.meta.assumption_state == "invalid":
                diagnostics.append("invalid_assumption_state")

        git_distance = get_git_commit_distance(record.path, repo_root=repo_root)
        reasons = [
            f"derived_status={derived_status}",
            f"eligible={str(eligible).lower()}",
            f"meta_status={record.meta.status}",
            f"priority={record.meta.priority}",
            f"unlock_count={unlock_counts.get(record.name, 0)}",
            f"assumption_state={record.meta.assumption_state}",
            f"evidence={record.meta.evidence}",
        ]
        if git_distance is not None:
            reasons.append(f"git_commit_distance={git_distance}")
        else:
            reasons.append("git_commit_distance=unknown")
        if unresolved_dependencies:
            reasons.append("unresolved_dependencies=" + ",".join(unresolved_dependencies))
        if missing_dependencies:
            reasons.append("missing_dependencies=" + ",".join(missing_dependencies))
        for diagnostic in diagnostics:
            reasons.append(f"diagnostic={diagnostic}")

        evaluated.append(
            EvaluatedRecord(
                record=record,
                unlock_count=unlock_counts.get(record.name, 0),
                derived_status=derived_status,
                eligible=eligible,
                unresolved_dependencies=tuple(unresolved_dependencies),
                missing_dependencies=tuple(missing_dependencies),
                diagnostics=tuple(diagnostics),
                git_commit_distance=git_distance,
                reasons=tuple(reasons),
            )
        )

    return evaluated


def filter_records(
    records: list[EvaluatedRecord],
    *,
    status: Optional[str] = None,
    meta_status: Optional[str] = None,
    change_type: Optional[str] = None,
    priority: Optional[str] = None,
    evidence: Optional[str] = None,
    assumption_state: Optional[str] = None,
    backlog_only: bool = False,
) -> list[EvaluatedRecord]:
    filtered = []
    for record in records:
        meta = record.record.meta
        if backlog_only and not record.eligible:
            continue
        if status and record.derived_status != status:
            continue
        if meta_status and meta.status != meta_status:
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


def rank_records(records: list[EvaluatedRecord]) -> list[EvaluatedRecord]:
    def sort_key(record: EvaluatedRecord):
        meta = record.record.meta
        git_distance = record.git_commit_distance if record.git_commit_distance is not None else 10**9
        return (
            DERIVED_STATUS_ORDER[record.derived_status],
            PRIORITY_ORDER[meta.priority],
            git_distance,
            -record.unlock_count,
            ASSUMPTION_ORDER[meta.assumption_state],
            EVIDENCE_ORDER[meta.evidence],
            record.record.name,
        )

    return sorted(records, key=sort_key)


def build_parser():
    parser = argparse.ArgumentParser(
        description="Recommend non-archived OpenSpec changes from repository-derived eligibility and ranking."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List matching changes.")
    next_parser = subparsers.add_parser("next", help="Recommend the next eligible change.")

    for subparser in (list_parser, next_parser):
        subparser.add_argument(
            "--status",
            choices=tuple(DERIVED_STATUS_ORDER.keys()),
            help="Filter by derived recommendation status.",
        )
        subparser.add_argument(
            "--meta-status",
            help="Filter by raw metadata status.",
        )
        subparser.add_argument("--type", dest="change_type", help="Filter by change type.")
        subparser.add_argument("--priority", help="Filter by priority.")
        subparser.add_argument("--evidence", help="Filter by evidence target.")
        subparser.add_argument("--assumption-state", help="Filter by assumption state.")
        subparser.add_argument(
            "--backlog",
            action="store_true",
            help="Shortcut for recommendable backlog view, equivalent to --status eligible.",
        )
        subparser.add_argument(
            "--json",
            action="store_true",
            help="Emit JSON instead of human-readable text.",
        )

    return parser


def _collect_records(args) -> list[EvaluatedRecord]:
    records = load_change_records()
    evaluated = evaluate_records(records)
    filtered = filter_records(
        evaluated,
        status=args.status,
        meta_status=args.meta_status,
        change_type=args.change_type,
        priority=args.priority,
        evidence=args.evidence,
        assumption_state=args.assumption_state,
        backlog_only=args.backlog or args.command == "next",
    )
    return rank_records(filtered)


def _serialize(rankings: list[EvaluatedRecord]) -> list[dict[str, object]]:
    payload = []
    for item in rankings:
        record = item.record
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
                "derived": {
                    "status": item.derived_status,
                    "eligible": item.eligible,
                    "diagnostics": list(item.diagnostics),
                    "unresolved_dependencies": list(item.unresolved_dependencies),
                    "missing_dependencies": list(item.missing_dependencies),
                    "git_commit_distance": item.git_commit_distance,
                },
                "unlock_count": item.unlock_count,
                "reasons": list(item.reasons),
            }
        )
    return payload


def _print_human_list(rankings: list[EvaluatedRecord], command: str):
    if not rankings:
        print("No matching changes.")
        return

    if command == "next":
        item = rankings[0]
        print(f"Recommended next change: {item.record.name}")
        for reason in item.reasons:
            print(f"- {reason}")
        return

    for item in rankings:
        print(item.record.name)
        for reason in item.reasons:
            print(f"- {reason}")


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.backlog and args.status and args.status != "eligible":
        parser.error("--backlog is equivalent to --status eligible and cannot be combined with a different status.")
    if args.backlog:
        args.status = "eligible"

    rankings = _collect_records(args)
    if args.json:
        print(json.dumps(_serialize(rankings), ensure_ascii=False, indent=2))
    else:
        _print_human_list(rankings, args.command)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
