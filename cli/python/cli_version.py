#!/usr/bin/env python3
"""CLI version identity and the mixed-installation guards built on it.

The CLI executable and the Unity Editor scripts ship as one package release, so
their versions are equal by construction. This module resolves the CLI's own
version and compares it against the two observable counterparts: the
`package.json` of a package tree the executable is installed in, and the
`bridge_version` reported by the Unity control service.
"""
import json
import sys
from pathlib import Path


PACKAGE_ID = "com.txcombo.unity-puer-exec"

STATUS_VERSION_MISMATCH = "version_mismatch"
UNKNOWN_VERSION_TEXT = "unknown"

GUARD_CLI_VERSION_UNKNOWN = "cli_version_unknown"
GUARD_PACKAGE_LAYOUT = "package_layout"
GUARD_BRIDGE = "bridge"
GUARD_BRIDGE_VERSION_UNKNOWN = "bridge_version_unknown"


def is_frozen():
    """True when running from a PyInstaller onefile build."""
    return bool(getattr(sys, "frozen", False))


def read_package_version(package_json_path):
    """Return the `version` field of a package.json, or None when unreadable."""
    try:
        with open(str(package_json_path), "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    version = data.get("version")
    if isinstance(version, str) and version:
        return version
    return None


def _read_package_name(package_json_path):
    try:
        with open(str(package_json_path), "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    name = data.get("name")
    return name if isinstance(name, str) else None


def stamped_version():
    """Return the version stamped into a frozen build, or None when absent."""
    try:
        import _build_version  # noqa: PLC0415 - generated at build time, absent from source.
    except ImportError:
        return None
    version = getattr(_build_version, "CLI_VERSION", None)
    if isinstance(version, str) and version:
        return version
    return None


def source_tree_package_json():
    return Path(__file__).resolve().parents[2] / "packages" / PACKAGE_ID / "package.json"


def source_tree_version():
    """Return the source-tree package version for a non-frozen invocation."""
    return read_package_version(source_tree_package_json())


def resolve_cli_version():
    """Return the acting CLI version, or None when it cannot be established.

    A frozen build resolves only from its build-time stamp; it never falls back to
    a `package.json` on the invoking machine, because an unstamped binary beside an
    unrelated package tree is exactly the shape that hides a mixed installation.
    """
    if is_frozen():
        return stamped_version()
    return source_tree_version()


def version_text(cli_version):
    return cli_version if cli_version else UNKNOWN_VERSION_TEXT


def executable_path(argv0=None):
    """Path of the running CLI entry point, or None when it cannot be determined."""
    if is_frozen():
        return Path(sys.executable).resolve()
    if argv0:
        return Path(argv0).resolve()
    return None


def find_containing_package_root(exe_path):
    """Return the installed package root containing `exe_path`, or None."""
    if exe_path is None:
        return None
    for parent in Path(exe_path).parents:
        candidate = parent / "package.json"
        if candidate.is_file() and _read_package_name(candidate) == PACKAGE_ID:
            return parent
    return None


def _mismatch(guard, cli_version, observed_version, observed_location):
    return {
        "guard": guard,
        "cli_version": version_text(cli_version),
        "observed_version": observed_version,
        "observed_location": observed_location,
    }


def check_cli_version_known(cli_version, argv0=None):
    """Refuse when a frozen build cannot state its own version."""
    if cli_version:
        return None
    exe_path = executable_path(argv0)
    return _mismatch(
        GUARD_CLI_VERSION_UNKNOWN,
        cli_version,
        None,
        str(exe_path) if exe_path is not None else None,
    )


def check_package_layout(cli_version, argv0=None, exe_path=None):
    """Compare the CLI version against the package tree the executable lives in.

    Returns None when the versions agree or when the executable is not inside a
    package tree; a standalone copy is a legitimate deployment, not a mismatch.
    This check performs no network activity.
    """
    if not cli_version:
        return None
    resolved_exe = exe_path if exe_path is not None else executable_path(argv0)
    package_root = find_containing_package_root(resolved_exe)
    if package_root is None:
        return None
    declared = read_package_version(package_root / "package.json")
    if declared == cli_version:
        return None
    return _mismatch(GUARD_PACKAGE_LAYOUT, cli_version, declared, str(package_root))


def check_bridge(cli_version, base_url, health_payload, require_version=True):
    """Compare the CLI version against a control service's `bridge_version`.

    `require_version=False` is used on pre-`ready` health payloads, which carry no
    identity fields yet: those fire only on an observed disagreement, so the guard
    lands on the first payload that actually carries `bridge_version`.
    """
    if not isinstance(health_payload, dict):
        return None
    bridge_version = health_payload.get("bridge_version")
    if not isinstance(bridge_version, str) or not bridge_version:
        if not require_version:
            return None
        return _mismatch(GUARD_BRIDGE_VERSION_UNKNOWN, cli_version, None, base_url)
    if cli_version and bridge_version == cli_version:
        return None
    return _mismatch(GUARD_BRIDGE, cli_version, bridge_version, base_url)


_MISMATCH_MESSAGES = {
    GUARD_CLI_VERSION_UNKNOWN: (
        "This build cannot report its own version, so the installation cannot be verified."
    ),
    GUARD_PACKAGE_LAYOUT: (
        "CLI version {cli_version} does not match the package it is installed in "
        "({observed_version}) at {observed_location}."
    ),
    GUARD_BRIDGE: (
        "CLI version {cli_version} does not match the Unity bridge version "
        "{observed_version} reported by {observed_location}."
    ),
    GUARD_BRIDGE_VERSION_UNKNOWN: (
        "The Unity bridge at {observed_location} reported no version, so it cannot be "
        "verified against CLI version {cli_version}."
    ),
}


def mismatch_message(detail):
    template = _MISMATCH_MESSAGES.get(detail.get("guard"), "Version mismatch detected.")
    return template.format(
        cli_version=detail.get("cli_version"),
        observed_version=detail.get("observed_version"),
        observed_location=detail.get("observed_location"),
    )
