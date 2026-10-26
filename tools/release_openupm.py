import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import prepare_validation_host

PACKAGE_JSON_PATH = REPO_ROOT / "packages" / "com.txcombo.unity-puer-exec" / "package.json"
PACKAGE_NAME = prepare_validation_host.FORMAL_PACKAGE_NAME
# The host copy carries a published executable the repository neither ships nor
# validates, so it is excluded from content parity on both sides.
PARITY_EXCLUDED_TOP_LEVEL = ("CLI~",)
PARITY_DIFFERENCE_LIST_LIMIT = 10
VERSION_FIELD_PATTERN = re.compile(r'("version"\s*:\s*)"(?:[^"\\]|\\.)*"')
REAL_HOST_ENV = "UNITY_PUER_EXEC_RUN_REAL_HOST_TESTS"
DEFAULT_UNIT_TEST_MODULES = (
    "tests.test_cleanup_validation_host_tool",
    "tests.test_direct_exec_client",
    "tests.test_openspec_backlog",
    "tests.test_openspec_change_meta",
    "tests.test_package_layout",
    "tests.test_prepare_validation_host_tool",
    "tests.test_unity_log_brief",
    "tests.test_unity_puer_session",
    "tests.test_unity_session",
    "tests.test_unity_session_cli",
    "tests.test_unity_session_modules",
)
REAL_HOST_TEST_MODULE = "tests.test_real_host_integration"
VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")


class ReleaseError(RuntimeError):
    pass


def _command_display(command, extra_env=None):
    prefix = ""
    if extra_env:
        prefix = " ".join("{}={}".format(key, value) for key, value in sorted(extra_env.items())) + " "
    return prefix + subprocess.list2cmdline(command)


def run_command(command, extra_env=None):
    env = None if not extra_env else {**os.environ, **extra_env}
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    if completed.returncode != 0:
        raise ReleaseError(
            "Command failed ({}): {}".format(
                completed.returncode,
                completed.stderr.strip() or completed.stdout.strip() or _command_display(command, extra_env),
            )
        )
    return completed


def run_python_module_tests(modules, extra_env=None):
    command = [sys.executable, "-m", "unittest", *modules]
    run_command(command, extra_env=extra_env)
    return _command_display(command, extra_env)


def read_package_json():
    return json.loads(PACKAGE_JSON_PATH.read_text(encoding="utf-8"))


def read_package_version():
    return str(read_package_json()["version"])


def write_package_version(version):
    package_json = read_package_json()
    package_json["version"] = version
    PACKAGE_JSON_PATH.write_text(
        json.dumps(package_json, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def repo_package_root():
    """The package directory this repository publishes.

    Derived from ``PACKAGE_JSON_PATH`` so a narrow override of that path also
    moves the package root.
    """
    return PACKAGE_JSON_PATH.parent


def _paths_equal(first, second):
    first_resolved = Path(first).resolve()
    second_resolved = Path(second).resolve()
    if os.name == "nt":
        return str(first_resolved).lower() == str(second_resolved).lower()
    return first_resolved == second_resolved


def _read_declared_version(package_root):
    package_json_path = Path(package_root) / "package.json"
    try:
        package_data = json.loads(package_json_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(package_data, dict):
        return None
    version = package_data.get("version")
    return None if version is None else str(version)


def _resolve_file_dependency(manifest_path, dependency_value):
    """Resolve a manifest ``file:`` value to a directory, or ``None``.

    ``compute_file_dependency`` writes two forms: a path relative to the
    manifest's own directory (``file:../../..``) and an absolute POSIX path
    (``file:///F:/...``). A registry version or git URL resolves to ``None``.
    """
    if not isinstance(dependency_value, str) or not dependency_value.startswith("file:"):
        return None

    target = dependency_value[len("file:"):]
    packages_path = Path(manifest_path).parent
    if target.startswith("///"):
        candidate = Path(target[3:])
    else:
        candidate = packages_path / target
    try:
        return candidate.resolve()
    except OSError:
        return candidate.absolute()


def _package_relative_files(package_root):
    """Relative POSIX paths of every package file, excluding ``CLI~/``."""
    root = Path(package_root)
    relative_paths = set()
    for dir_path, dir_names, file_names in os.walk(str(root)):
        current = Path(dir_path)
        relative_dir = current.relative_to(root)
        if relative_dir == Path("."):
            dir_names[:] = [
                name for name in dir_names if name not in PARITY_EXCLUDED_TOP_LEVEL
            ]
        for file_name in file_names:
            relative_file = relative_dir / file_name
            relative_paths.add(relative_file.as_posix())
    return relative_paths


def _normalise_line_endings(text):
    return text.replace("\r\n", "\n")


def _package_json_without_version(package_json_path):
    try:
        package_data = json.loads(Path(package_json_path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(package_data, dict):
        return None
    package_data.pop("version", None)
    return package_data


def _same_package_file(host_root, repo_root, relative_path):
    if relative_path == "package.json":
        host_document = _package_json_without_version(Path(host_root) / relative_path)
        repo_document = _package_json_without_version(Path(repo_root) / relative_path)
        if host_document is not None and repo_document is not None:
            return host_document == repo_document

    host_bytes = (Path(host_root) / relative_path).read_bytes()
    repo_bytes = (Path(repo_root) / relative_path).read_bytes()
    if host_bytes == repo_bytes:
        return True
    try:
        host_text = host_bytes.decode("utf-8")
        repo_text = repo_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return _normalise_line_endings(host_text) == _normalise_line_endings(repo_text)


def compare_package_trees(host_root, repo_root):
    """Relative paths whose package content differs, sorted."""
    host_files = _package_relative_files(host_root)
    repo_files = _package_relative_files(repo_root)

    differing = set(host_files ^ repo_files)
    for relative_path in sorted(host_files & repo_files):
        if not _same_package_file(host_root, repo_root, relative_path):
            differing.add(relative_path)
    return sorted(differing)


def _describe_differences(differing_paths):
    listed = differing_paths[:PARITY_DIFFERENCE_LIST_LIMIT]
    description = ", ".join(listed)
    if len(differing_paths) > len(listed):
        description += ", ..."
    return "{} differing path(s): {}".format(len(differing_paths), description)


def evaluate_host_package(candidate_version, sync_requested=False):
    """Establish that the validation host would load the release candidate.

    Read-only. Returns a structured verdict and raises ``ReleaseError`` with a
    refusal code when the host is unusable, ambiguous, unwired, lagging, or
    content-divergent. The candidate version is compared against the loaded
    tree's declared version; the repository still holds the current version at
    this point, so identity by path is the only correct answer while the bump
    has not happened yet.
    """
    verdict = {
        "code": None,
        "ok": False,
        "host_project": None,
        "manifest_path": None,
        "loaded_via": None,
        "loaded_root": None,
        "identity": None,
        "observed_version": None,
        "expected_version": candidate_version,
        "parity": None,
        "alignment_status": "not_requested",
    }

    try:
        host_project = prepare_validation_host.resolve_project_path()
    except ValueError as exc:
        raise ReleaseError("host_project_unavailable: {}".format(exc))
    verdict["host_project"] = str(host_project)

    if not host_project.is_dir():
        raise ReleaseError(
            "host_project_unavailable: validation host project directory does not exist: {}".format(
                host_project
            )
        )
    manifest_path = prepare_validation_host.project_path_to_manifest_path(host_project)
    if not manifest_path.is_file():
        raise ReleaseError(
            "host_project_unavailable: validation host manifest is missing: {}".format(manifest_path)
        )
    verdict["manifest_path"] = str(manifest_path)

    package_root = repo_package_root()
    _shadowing, embedded_first, embedded_paths = prepare_validation_host.detect_embedded_package_shadowing(
        manifest_path, package_root=package_root
    )
    if len(embedded_paths) > 1:
        raise ReleaseError(
            "host_package_ambiguous: {} immediate children of {} declare {}: {}".format(
                len(embedded_paths),
                manifest_path.parent,
                PACKAGE_NAME,
                ", ".join(embedded_paths),
            )
        )

    if embedded_paths:
        loaded_via = "embedded"
        loaded_root = Path(embedded_first)
    else:
        try:
            manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ReleaseError(
                "host_project_unavailable: validation host manifest is not readable JSON: {} ({})".format(
                    manifest_path, exc
                )
            )
        dependencies = manifest_data.get("dependencies") if isinstance(manifest_data, dict) else None
        if not isinstance(dependencies, dict):
            dependencies = {}
        resolved = _resolve_file_dependency(manifest_path, dependencies.get(PACKAGE_NAME))
        if resolved is None:
            raise ReleaseError(
                "host_package_not_wired: {} declares no usable file: dependency for {}; "
                "the host would not load this package.".format(manifest_path, PACKAGE_NAME)
            )
        loaded_via = "file"
        loaded_root = resolved

    verdict["loaded_via"] = loaded_via
    verdict["loaded_root"] = str(loaded_root)

    if not (loaded_root / "package.json").is_file():
        raise ReleaseError(
            "host_package_not_wired: the loaded package path has no package.json: {}".format(loaded_root)
        )

    if loaded_via == "file" and _paths_equal(loaded_root, package_root):
        verdict["identity"] = "repository_package"
        verdict["ok"] = True
        verdict["alignment_status"] = "not_needed" if sync_requested else "not_requested"
        return verdict

    verdict["identity"] = "host_copy"
    observed_version = _read_declared_version(loaded_root)
    if observed_version is None:
        raise ReleaseError(
            "host_package_not_wired: the loaded package declares no version: {}".format(
                loaded_root / "package.json"
            )
        )
    verdict["observed_version"] = observed_version

    version_matches = observed_version == candidate_version
    if not version_matches and not sync_requested:
        raise ReleaseError(
            "host_package_version_mismatch: the validation host would load {} declaring version {}; "
            "the release candidate is {}. Align the host copy with --sync-host-version, or remove the "
            "embedded copy so the file: dependency wins.".format(
                loaded_root, observed_version, candidate_version
            )
        )

    if sync_requested:
        differing_paths = compare_package_trees(loaded_root, package_root)
        verdict["parity"] = {
            "checked": True,
            "ok": not differing_paths,
            "difference_count": len(differing_paths),
            "differing_paths": differing_paths[:PARITY_DIFFERENCE_LIST_LIMIT],
        }
        if differing_paths:
            raise ReleaseError(
                "host_package_stale: host package content at {} differs from the repository package at {}: {}. "
                "Sync the host copy from this repository, or remove the embedded copy so the file: dependency "
                "wins.".format(
                    loaded_root, package_root, _describe_differences(differing_paths)
                )
            )

    verdict["ok"] = True
    if version_matches:
        verdict["alignment_status"] = "not_needed" if sync_requested else "not_requested"
    else:
        verdict["alignment_status"] = "would_align"
    return verdict


def stamp_package_version_text(original_text, version):
    """Replace only the ``version`` value, preserving every other byte."""
    stamped_text, replacements = VERSION_FIELD_PATTERN.subn(
        lambda match: match.group(1) + json.dumps(version),
        original_text,
        count=1,
    )
    if replacements != 1:
        raise ReleaseError("host_package_write_failed: package.json declares no version field to align.")

    expected_document = json.loads(original_text)
    observed_document = json.loads(stamped_text)
    expected_document["version"] = version
    if observed_document != expected_document:
        raise ReleaseError("host_package_write_failed: aligning the version changed other package fields.")
    return stamped_text


def align_host_package_version(loaded_root, version):
    """Write the candidate version into the host copy; return its original bytes."""
    package_json_path = Path(loaded_root) / "package.json"
    original_bytes = package_json_path.read_bytes()
    stamped_text = stamp_package_version_text(original_bytes.decode("utf-8"), version)
    try:
        package_json_path.write_bytes(stamped_text.encode("utf-8"))
    except OSError as exc:
        try:
            package_json_path.write_bytes(original_bytes)
        except OSError:
            pass
        raise ReleaseError(
            "host_package_write_failed: cannot write {}: {}".format(package_json_path, exc)
        )
    return original_bytes


def ensure_valid_version(version):
    if not VERSION_PATTERN.match(version):
        raise ReleaseError("Version must use x.y.z numeric format.")


def ensure_clean_worktree():
    completed = run_command(["git", "status", "--porcelain"])
    if completed.stdout.strip():
        raise ReleaseError("Release preparation requires a clean working tree.")


def ensure_tag_available(tag_name):
    local = subprocess.run(
        ["git", "rev-parse", "-q", "--verify", "refs/tags/{}".format(tag_name)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if local.returncode == 0 and local.stdout.strip():
        raise ReleaseError("Release tag {} already exists locally.".format(tag_name))

    origin = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if origin.returncode != 0:
        return {"local_checked": True, "remote_checked": False}

    remote = run_command(["git", "ls-remote", "--tags", "origin", "refs/tags/{}".format(tag_name)])
    if remote.stdout.strip():
        raise ReleaseError("Release tag {} already exists on origin.".format(tag_name))
    return {"local_checked": True, "remote_checked": True}


def build_next_steps(version, create_commit, create_tag):
    tag_name = "v{}".format(version)
    steps = []
    if create_tag:
        steps.append("No push was performed. Review the local release commit and {} tag.".format(tag_name))
        steps.append("Push the release commit and tag manually to trigger CI publishing.")
        return steps
    if create_commit:
        steps.append("No push was performed. Create local tag {} when ready.".format(tag_name))
        steps.append("Push the release commit and tag manually to trigger CI publishing.")
        return steps
    steps.append("No commit or tag was created. Review the version bump and create a release commit when ready.")
    steps.append("Create local tag {} after the release commit, then push both manually to trigger CI publishing.".format(tag_name))
    return steps


def perform_release(
    version,
    create_commit=False,
    create_tag=False,
    dry_run=False,
    real_host_validation=False,
    sync_host_version=False,
):
    ensure_valid_version(version)
    if create_tag and not create_commit:
        raise ReleaseError("Creating a release tag requires committed release state. Use --commit with --tag.")
    if sync_host_version and not real_host_validation:
        raise ReleaseError("Host version alignment requires --real-host-validation.")

    ensure_clean_worktree()
    tag_name = "v{}".format(version)
    tag_checks = ensure_tag_available(tag_name)
    current_version = read_package_version()
    if current_version == version:
        raise ReleaseError("package.json already uses version {}.".format(version))

    # Read-only, and before either the dry-run return or the version write, so a
    # host that cannot validate this candidate costs seconds instead of a full
    # real-host suite run and leaves nothing to roll back.
    host_package = (
        evaluate_host_package(version, sync_requested=sync_host_version)
        if real_host_validation
        else None
    )

    unit_test_command = _command_display([sys.executable, "-m", "unittest", *DEFAULT_UNIT_TEST_MODULES])
    real_host_command = _command_display(
        [sys.executable, "-m", "unittest", REAL_HOST_TEST_MODULE],
        extra_env={REAL_HOST_ENV: "1"},
    )
    result = {
        "status": "dry-run" if dry_run else "prepared",
        "package_json": str(PACKAGE_JSON_PATH),
        "current_version": current_version,
        "requested_version": version,
        "tag": tag_name,
        "dry_run": dry_run,
        "commit_requested": create_commit,
        "tag_requested": create_tag,
        "real_host_validation": {
            "enabled": real_host_validation,
            "default_behavior": "skipped",
            "command": real_host_command,
            "host_package": host_package,
        },
        "preflight": {
            "worktree_clean": True,
            "tag_checks": tag_checks,
        },
        "tests": {
            "default_unit": unit_test_command,
        },
        "planned_actions": [
            "Update package.json version from {} to {}.".format(current_version, version),
            "Run default mocked/unit release test suite.",
        ],
        "executed_actions": [],
        "next_steps": build_next_steps(version, create_commit, create_tag),
    }
    alignment_needed = bool(host_package) and host_package["alignment_status"] == "would_align"
    if alignment_needed:
        result["planned_actions"].append(
            "Align host package version at {} from {} to {}.".format(
                host_package["loaded_root"], host_package["observed_version"], version
            )
        )
    if real_host_validation:
        result["planned_actions"].append("Run opt-in real-host validation.")
    if create_commit:
        result["planned_actions"].append('Create local git commit "Release {}".'.format(tag_name))
    if create_tag:
        result["planned_actions"].append("Create local git tag {}.".format(tag_name))

    if dry_run:
        return result

    host_package_json_bytes = None
    if alignment_needed:
        # The host write precedes the repository bump: a failed host write ends
        # the run before anything else changes.
        host_package_json_bytes = align_host_package_version(host_package["loaded_root"], version)
        host_package["alignment_status"] = "aligned"
        result["executed_actions"].append(
            "Aligned host package version at {} from {} to {}.".format(
                host_package["loaded_root"], host_package["observed_version"], version
            )
        )

    release_committed = False
    try:
        write_package_version(version)
        result["executed_actions"].append("Updated package.json version to {}.".format(version))

        run_python_module_tests(DEFAULT_UNIT_TEST_MODULES)
        result["executed_actions"].append("Ran default mocked/unit release test suite.")

        if real_host_validation:
            run_python_module_tests((REAL_HOST_TEST_MODULE,), extra_env={REAL_HOST_ENV: "1"})
            result["executed_actions"].append("Ran opt-in real-host validation.")

        if create_commit:
            run_command(["git", "add", str(PACKAGE_JSON_PATH)])
            commit_message = "Release {}".format(tag_name)
            run_command(["git", "commit", "-m", commit_message])
            result["executed_actions"].append('Created local git commit "{}".'.format(commit_message))
            release_committed = True

        if create_tag:
            run_command(["git", "tag", tag_name])
            result["executed_actions"].append("Created local git tag {}.".format(tag_name))
    except BaseException:
        # A real-host suite runs for over half an hour, so an interrupt is the
        # likeliest early ending; both halves of the transaction roll back.
        if not release_committed:
            try:
                write_package_version(current_version)
            finally:
                if host_package_json_bytes is not None:
                    (Path(host_package["loaded_root"]) / "package.json").write_bytes(
                        host_package_json_bytes
                    )
                    host_package["alignment_status"] = "rolled_back"
        raise

    return result


def build_parser():
    parser = argparse.ArgumentParser(
        description="Prepare a local OpenUPM source release without pushing to the remote."
    )
    parser.add_argument("--version", required=True, help="Requested package version in x.y.z format.")
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Create a local release commit after the version update and tests succeed.",
    )
    parser.add_argument(
        "--tag",
        action="store_true",
        help="Create a local source tag after the release state is committed.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report the planned release actions without changing repository state.",
    )
    parser.add_argument(
        "--real-host-validation",
        action="store_true",
        help="Run the opt-in real-host integration validation after the default unit suite.",
    )
    parser.add_argument(
        "--sync-host-version",
        action="store_true",
        help=(
            "With --real-host-validation, write the release candidate version into the host's loaded "
            "package copy when its package content matches this repository."
        ),
    )
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = perform_release(
            version=args.version,
            create_commit=args.commit,
            create_tag=args.tag,
            dry_run=args.dry_run,
            real_host_validation=args.real_host_validation,
            sync_host_version=args.sync_host_version,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except ReleaseError as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
