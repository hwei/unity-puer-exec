import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_JSON_PATH = REPO_ROOT / "packages" / "com.txcombo.unity-puer-exec" / "package.json"
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


def perform_release(version, create_commit=False, create_tag=False, dry_run=False, real_host_validation=False):
    ensure_valid_version(version)
    if create_tag and not create_commit:
        raise ReleaseError("Creating a release tag requires committed release state. Use --commit with --tag.")

    ensure_clean_worktree()
    tag_name = "v{}".format(version)
    tag_checks = ensure_tag_available(tag_name)
    current_version = read_package_version()
    if current_version == version:
        raise ReleaseError("package.json already uses version {}.".format(version))

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
    if real_host_validation:
        result["planned_actions"].append("Run opt-in real-host validation.")
    if create_commit:
        result["planned_actions"].append('Create local git commit "Release {}".'.format(tag_name))
    if create_tag:
        result["planned_actions"].append("Create local git tag {}.".format(tag_name))

    if dry_run:
        return result

    release_committed = False
    write_package_version(version)
    result["executed_actions"].append("Updated package.json version to {}.".format(version))
    try:
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
    except ReleaseError:
        if not release_committed:
            write_package_version(current_version)
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
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except ReleaseError as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
