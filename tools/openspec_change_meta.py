from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable, Optional


REPO_ROOT = Path(__file__).resolve().parents[1]
CHANGE_TEMPLATE_PATH = REPO_ROOT / "openspec" / "templates" / "change-meta.yaml"
CHANGES_DIR = REPO_ROOT / "openspec" / "changes"
ARCHIVE_DIR = CHANGES_DIR / "archive"

# `queued` and `active` remain accepted as legacy raw metadata values so older
# non-archived changes can still be loaded during the migration.
ALLOWED_STATUS = ("queued", "active", "blocked", "superseded")
ALLOWED_CHANGE_TYPE = ("feature", "harness", "validation", "refactor", "spike")
ALLOWED_PRIORITY = ("P0", "P1", "P2")
ALLOWED_ASSUMPTION_STATE = ("valid", "needs-review", "invalid")
ALLOWED_EVIDENCE = ("tests", "host-validation", "cli-transcript", "manual-check")


@dataclass(frozen=True)
class ChangeMeta:
    status: Optional[str]
    change_type: str
    priority: str
    blocked_by: tuple[str, ...]
    assumption_state: str
    evidence: str
    updated_at: str


def _validate_choice(value: str, allowed: Iterable[str], field_name: str) -> str:
    if value not in allowed:
        raise ValueError(f"Unsupported {field_name} '{value}'. Allowed values: {', '.join(allowed)}")
    return value


def _validate_date(value: str) -> str:
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"updated_at must be an ISO date, got '{value}'") from exc
    return value


def normalize_meta(raw: dict[str, object]) -> ChangeMeta:
    blocked_by = raw.get("blocked_by", [])
    if blocked_by in ("[]", None):
        blocked_values: list[str] = []
    elif isinstance(blocked_by, list):
        blocked_values = [str(item) for item in blocked_by]
    else:
        raise ValueError("blocked_by must be a list.")

    raw_status = raw.get("status")
    normalized_status = None if raw_status in ("", None) else _validate_choice(str(raw_status), ALLOWED_STATUS, "status")

    return ChangeMeta(
        status=normalized_status,
        change_type=_validate_choice(str(raw["change_type"]), ALLOWED_CHANGE_TYPE, "change_type"),
        priority=_validate_choice(str(raw["priority"]), ALLOWED_PRIORITY, "priority"),
        blocked_by=tuple(blocked_values),
        assumption_state=_validate_choice(
            str(raw["assumption_state"]), ALLOWED_ASSUMPTION_STATE, "assumption_state"
        ),
        evidence=_validate_choice(str(raw["evidence"]), ALLOWED_EVIDENCE, "evidence"),
        updated_at=_validate_date(str(raw["updated_at"])),
    )


def parse_meta_text(text: str) -> ChangeMeta:
    data: dict[str, object] = {}
    current_list_key: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("- "):
            if current_list_key is None:
                raise ValueError("List item found before a list key.")
            data.setdefault(current_list_key, [])
            assert isinstance(data[current_list_key], list)
            data[current_list_key].append(line[2:].strip())
            continue

        current_list_key = None
        if ":" not in line:
            raise ValueError(f"Invalid metadata line: '{raw_line}'")

        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value == "":
            data[key] = []
            current_list_key = key
        elif value == "[]":
            data[key] = []
        else:
            data[key] = value

    required = {"change_type", "priority", "blocked_by", "assumption_state", "evidence", "updated_at"}
    missing = required - data.keys()
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(f"Missing required metadata fields: {missing_text}")

    return normalize_meta(data)


def load_meta(meta_path: Path) -> ChangeMeta:
    return parse_meta_text(meta_path.read_text(encoding="utf-8"))


def dump_meta(meta: ChangeMeta) -> str:
    lines = []
    if meta.status is not None:
        lines.append(f"status: {meta.status}")
    lines.extend(
        [
            f"change_type: {meta.change_type}",
            f"priority: {meta.priority}",
        ]
    )
    if meta.blocked_by:
        lines.append("blocked_by:")
        lines.extend(f"- {item}" for item in meta.blocked_by)
    else:
        lines.append("blocked_by: []")
    lines.extend(
        [
            f"assumption_state: {meta.assumption_state}",
            f"evidence: {meta.evidence}",
            f"updated_at: {meta.updated_at}",
        ]
    )
    return "\n".join(lines) + "\n"


def meta_path_for_change(change_dir: Path) -> Path:
    return change_dir / "meta.yaml"


def ensure_meta_file(change_dir: Path, defaults: Optional[dict[str, object]] = None) -> Path:
    defaults = dict(defaults or {})
    template_meta = load_meta(CHANGE_TEMPLATE_PATH)
    normalized_defaults = {
        "change_type": defaults.get("change_type", template_meta.change_type),
        "priority": defaults.get("priority", template_meta.priority),
        "blocked_by": defaults.get("blocked_by", list(template_meta.blocked_by)),
        "assumption_state": defaults.get("assumption_state", template_meta.assumption_state),
        "evidence": defaults.get("evidence", template_meta.evidence),
        "updated_at": defaults.get("updated_at", date.today().isoformat()),
    }
    if "status" in defaults:
        normalized_defaults["status"] = defaults["status"]
    elif template_meta.status is not None:
        normalized_defaults["status"] = template_meta.status
    meta = normalize_meta(normalized_defaults)
    meta_path = meta_path_for_change(change_dir)
    meta_path.write_text(dump_meta(meta), encoding="utf-8")
    return meta_path


def list_non_archived_change_dirs(changes_dir: Path = CHANGES_DIR) -> list[Path]:
    if not changes_dir.exists():
        return []
    change_dirs = []
    for path in sorted(changes_dir.iterdir()):
        if not path.is_dir() or path.name == "archive":
            continue
        change_dirs.append(path)
    return change_dirs
