import argparse
import json
import shutil
from pathlib import Path

import prepare_validation_host


DECLARED_VALIDATION_TEMP_ROOTS = (
    Path("Assets") / "__AgentValidation",
    Path("Assets") / "__codex_validation_temp",
    Path("Assets") / "CodexValidation",
)


def iter_declared_validation_temp_paths(project_path):
    project_root = Path(project_path).resolve()
    for relative_root in DECLARED_VALIDATION_TEMP_ROOTS:
        root_path = project_root / relative_root
        yield root_path
        meta_path = root_path.with_name(root_path.name + ".meta")
        yield meta_path


def collect_residue(project_path):
    residue = []
    for candidate in iter_declared_validation_temp_paths(project_path):
        if candidate.exists():
            residue.append(str(candidate))
    return residue


def assert_declared_validation_temp_path(project_path, relative_posix):
    """Refuse a cleanup target that is not a declared validation-temp root or its contents."""
    project_root = Path(project_path).resolve()
    relative = Path(relative_posix)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(
            "refusing validation-temp path outside the declared inventory: {}".format(relative_posix)
        )
    normalized = relative.as_posix()
    for root in DECLARED_VALIDATION_TEMP_ROOTS:
        root_posix = root.as_posix()
        allowed = (
            normalized == root_posix
            or normalized.startswith(root_posix + "/")
            or normalized == root_posix + ".meta"
        )
        if not allowed:
            continue
        candidate = (project_root / relative).resolve()
        try:
            candidate.relative_to(project_root)
        except ValueError as exc:
            raise ValueError(
                "refusing validation-temp path outside the declared inventory: {}".format(relative_posix)
            ) from exc
        return normalized
    raise ValueError(
        "refusing validation-temp path outside the declared inventory: {}".format(relative_posix)
    )


def _editor_asset_paths(project_root):
    """Asset paths DeleteAsset can remove. A root's .meta goes with the asset."""
    paths = []
    for candidate in iter_declared_validation_temp_paths(project_root):
        if not candidate.exists():
            continue
        relative = candidate.relative_to(project_root).as_posix()
        if relative.endswith(".meta"):
            asset_relative = relative[: -len(".meta")]
            if (project_root / asset_relative).exists():
                continue
        paths.append(assert_declared_validation_temp_path(project_root, relative))
    return paths


def _filesystem_delete(candidate, removed, errors):
    try:
        if candidate.is_dir():
            shutil.rmtree(candidate)
        else:
            candidate.unlink()
        removed.append(str(candidate))
    except OSError as exc:
        errors.append({"path": str(candidate), "error": str(exc)})


def cleanup_validation_temp_assets(project_path, editor_delete=None):
    """Remove declared validation-temp roots.

    ``editor_delete`` runs inside a live Editor (``AssetDatabase.DeleteAsset``).
    When it is supplied, the filesystem delete is not used: deleting a ``.meta``
    the Editor still has open is what raises ``Opening file failed``. With no
    live Editor, the filesystem delete remains the fallback.
    """
    project_root = Path(project_path).resolve()
    removed = []
    errors = []
    existing = [candidate for candidate in iter_declared_validation_temp_paths(project_root) if candidate.exists()]

    if existing and editor_delete is not None:
        asset_paths = _editor_asset_paths(project_root)
        try:
            editor_result = editor_delete(asset_paths) or {}
        except Exception as exc:  # noqa: BLE001 - recorded, not turned into an out-of-process delete.
            editor_result = {}
            errors.append({"path": "<editor>", "error": str(exc)})
        for item in editor_result.get("errors") or []:
            if isinstance(item, dict):
                errors.append(item)
            else:
                errors.append({"path": "<editor>", "error": str(item)})
        for candidate in existing:
            if not candidate.exists():
                removed.append(str(candidate))
    elif existing:
        for candidate in existing:
            _filesystem_delete(candidate, removed, errors)

    residue = collect_residue(project_root)
    if residue:
        status = "partial" if removed or errors else "residue_present"
    elif errors:
        status = "partial"
    elif removed:
        status = "cleaned"
    else:
        status = "already_clean"

    return {
        "status": status,
        "project_path": str(project_root),
        "declared_roots": [str(project_root / root) for root in DECLARED_VALIDATION_TEMP_ROOTS],
        "removed": removed,
        "errors": errors,
        "residue": residue,
    }


def build_parser():
    parser = argparse.ArgumentParser(
        description="Remove repository-owned temporary validation assets from the external Unity host project."
    )
    parser.add_argument(
        "--project-path",
        help="Path to the validation host Unity Project directory. Defaults to UNITY_PROJECT_PATH or .env.",
    )
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    project_path = prepare_validation_host.resolve_project_path(args.project_path)
    result = cleanup_validation_temp_assets(project_path)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if not result["residue"] and not result["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
