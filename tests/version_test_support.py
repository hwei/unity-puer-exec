"""Shared helpers for the CLI version identity and mixed-installation guards.

Two facts ripple across the whole suite once the guards exist:

- every machine-readable response now carries a top-level `cli_version`, so any
  assertion that compares a whole payload needs it stripped rather than pasted in;
- a *ready* health payload without `bridge_version` is now a refusal, so mocked
  ready payloads must carry the matching version to keep exercising their subject.

Both live here so the suite states each fact once.
"""
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CLI_DIR = REPO_ROOT / "cli" / "python"
if str(CLI_DIR) not in sys.path:
    sys.path.insert(0, str(CLI_DIR))

import cli_version  # type: ignore  # noqa: E402


def current_cli_version():
    """The version this CLI resolves for itself, i.e. the one a bridge must match."""
    return cli_version.resolve_cli_version()


def matching_bridge_version():
    return current_cli_version()


def with_matching_bridge_version(payload):
    """Return a copy of a ready health payload that passes the bridge guard."""
    updated = dict(payload)
    updated["bridge_version"] = matching_bridge_version()
    return updated


def strip_cli_version(body):
    """Drop the acting-build stamp so a golden comparison stays about its subject."""
    if not isinstance(body, dict):
        return body
    stripped = dict(body)
    stripped.pop("cli_version", None)
    return stripped


def assert_carries_cli_version(test_case, body):
    test_case.assertIsInstance(body, dict)
    test_case.assertIsInstance(body.get("cli_version"), str)
    test_case.assertTrue(body["cli_version"])
