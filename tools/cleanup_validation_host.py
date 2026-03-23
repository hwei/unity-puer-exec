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


def cleanup_validation_temp_assets(project_path):
    project_root = Path(project_path).resolve()
    removed = []
    errors = []

    for candidate in iter_declared_validation_temp_paths(project_root):
        if not candidate.exists():
            continue
        try:
            if candidate.is_dir():
                shutil.rmtree(candidate)
            else:
                candidate.unlink()
            removed.append(str(candidate))
        except OSError as exc:
            errors.append({"path": str(candidate), "error": str(exc)})

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
