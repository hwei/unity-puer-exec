import argparse
import json
import os
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
UNITY_PROJECT_PATH_ENV = "UNITY_PROJECT_PATH"
FORMAL_PACKAGE_NAME = "com.txcombo.unity-puer-exec"
LEGACY_PACKAGE_NAME = "com.c3.unity-puer-exec.validation"
FORMAL_PACKAGE_ROOT = REPO_ROOT / "packages" / FORMAL_PACKAGE_NAME


def _load_dotenv_path(env, dotenv_path):
    if not dotenv_path.exists():
        return False

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key and key not in env:
            env[key] = value.strip()
    return True


def resolve_project_path(project_path=None, env=None):
    if project_path:
        return Path(project_path).resolve()

    resolved_env = dict(os.environ if env is None else env)
    _load_dotenv_path(resolved_env, REPO_ROOT / ".env")
    env_project_path = resolved_env.get(UNITY_PROJECT_PATH_ENV)
    if env_project_path:
        return Path(env_project_path).resolve()

    raise ValueError(
        "Validation host project path is required. Pass --project-path or set {}.".format(
            UNITY_PROJECT_PATH_ENV
        )
    )


def project_path_to_manifest_path(project_path):
    return project_path / "Packages" / "manifest.json"


def compute_file_dependency(manifest_path, package_root=FORMAL_PACKAGE_ROOT):
    relative_path = os.path.relpath(package_root, manifest_path.parent)
    return "file:{}".format(relative_path.replace("\\", "/"))


def rewrite_manifest(manifest_data, manifest_path):
    dependencies = manifest_data.get("dependencies")
    if not isinstance(dependencies, dict):
        raise ValueError("manifest.json must contain a dependencies object.")

    expected_value = compute_file_dependency(manifest_path)
    current_value = dependencies.get(FORMAL_PACKAGE_NAME)
    legacy_value = dependencies.get(LEGACY_PACKAGE_NAME)

    if current_value == expected_value and LEGACY_PACKAGE_NAME not in dependencies:
        return manifest_data, False, expected_value

    rewritten_dependencies = {}
    replaced_legacy = False
    inserted_formal = False

    for key, value in dependencies.items():
        if key == LEGACY_PACKAGE_NAME:
            rewritten_dependencies[FORMAL_PACKAGE_NAME] = expected_value
            replaced_legacy = True
            inserted_formal = True
            continue
        if key == FORMAL_PACKAGE_NAME:
            rewritten_dependencies[key] = expected_value
            inserted_formal = True
            continue
        rewritten_dependencies[key] = value

    if not inserted_formal:
        rewritten_dependencies[FORMAL_PACKAGE_NAME] = expected_value

    rewritten_manifest = dict(manifest_data)
    rewritten_manifest["dependencies"] = rewritten_dependencies
    changed = replaced_legacy or legacy_value is not None or current_value != expected_value
    return rewritten_manifest, changed, expected_value


def write_manifest(manifest_path, manifest_data):
    manifest_path.write_text(
        json.dumps(manifest_data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def build_parser():
    parser = argparse.ArgumentParser(
        description="Rewrite a validation host manifest to consume the formal local Unity package."
    )
    parser.add_argument(
        "--project-path",
        help="Path to the validation host Unity Project directory. Defaults to UNITY_PROJECT_PATH or .env.",
    )
    parser.add_argument(
        "--manifest-path",
        help="Override the manifest path directly. When omitted, uses <project-path>/Packages/manifest.json.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the target dependency without writing manifest.json.",
    )
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.manifest_path:
        manifest_path = Path(args.manifest_path).resolve()
    else:
        project_path = resolve_project_path(args.project_path)
        manifest_path = project_path_to_manifest_path(project_path)

    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    rewritten_manifest, changed, dependency_value = rewrite_manifest(manifest_data, manifest_path)

    if not args.dry_run and changed:
        write_manifest(manifest_path, rewritten_manifest)

    status = "unchanged" if not changed else ("dry-run" if args.dry_run else "updated")
    print(
        json.dumps(
            {
                "status": status,
                "manifest_path": str(manifest_path),
                "package_name": FORMAL_PACKAGE_NAME,
                "dependency": dependency_value,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
