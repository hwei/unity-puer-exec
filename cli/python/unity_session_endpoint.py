#!/usr/bin/env python3
"""Decide a project's session state from project-local files the Editor authored.

This module replaces the CLI-authored session artifact. The difference is not the
file name, it is who is entitled to speak: the artifact was the CLI's claim about a
process it did not own, and it filled the process id from machine-wide tasklist
order, so on a machine with several projects open it could name an unrelated
project's Editor. Everything here is read from what the Editor published about
itself, corroborated by the project's own lockfile.

Two files decide the whole state space (design D2):

    Temp/UnityLockfile    Temp/UnityPuerExec/endpoint.json    Conclusion
    ──────────────────    ────────────────────────────────    ──────────────────
        absent                    absent                      no Editor
        held                      absent                      did not opt in
        held                      present                     controlled (verify)
        absent                    present                     crashed/killed residue

No machine-wide process listing participates in any of it.
"""
import json
import os
import time as time_module
from pathlib import Path

from unity_session_common import (
    ENDPOINT_RELATIVE_PATH,
    SERVICE_RESTART_GRACE_SECONDS,
)


# The four cells of the D2 table.
SESSION_STATE_NO_EDITOR = "no_editor"
SESSION_STATE_NOT_UNDER_CONTROL = "not_under_control"
SESSION_STATE_CONTROLLED = "controlled"
SESSION_STATE_ENDED_RESIDUE = "ended_residue"

# How the published console log path relates to this session, decided before a
# caller takes byte offsets against it (design D4).
OBSERVATION_PROJECT_PRIVATE = "project_private"
OBSERVATION_CALLER_DIRECTED = "caller_directed"
OBSERVATION_PLATFORM_DEFAULT_SOLE_EDITOR = "platform_default_sole_editor"
OBSERVATION_PLATFORM_DEFAULT_CONTENDED = "platform_default_contended"

# Reading can be denied while the Editor replaces the file, because a replacing
# rename and an ordinary read open deny each other on Windows. Measured at well
# under 0.1% of reads (task 1.3), and a brief retry cleared every occurrence.
READ_ATTEMPTS = 5
READ_RETRY_SECONDS = 0.01


def endpoint_publication_path(project_path):
    return Path(project_path) / ENDPOINT_RELATIVE_PATH


def _coerce_publication(payload):
    """Accept only a publication complete enough to act on.

    A partial record is treated as no record rather than as a partial answer: the
    whole point of the publication is that it is authoritative, and a half-filled
    one is not.
    """
    if not isinstance(payload, dict):
        return None
    port = payload.get("port")
    unity_pid = payload.get("unity_pid")
    project_path = payload.get("project_path")
    session_marker = payload.get("session_marker")
    if not isinstance(port, int) or isinstance(port, bool) or port <= 0:
        return None
    if not isinstance(unity_pid, int) or isinstance(unity_pid, bool) or unity_pid <= 0:
        return None
    if not isinstance(project_path, str) or not project_path:
        return None
    if not isinstance(session_marker, str) or not session_marker:
        return None

    publication = {
        "port": port,
        "unity_pid": unity_pid,
        "project_path": project_path,
        "session_marker": session_marker,
        "base_url": "http://127.0.0.1:{}".format(port),
    }
    console_log_path = payload.get("console_log_path")
    if isinstance(console_log_path, str) and console_log_path:
        publication["console_log_path"] = console_log_path
    return publication


def read_endpoint_publication(project_path, time_ref=None):
    """Read the Editor's publication, retrying a denial from a concurrent replace."""
    time_ref = time_module if time_ref is None else time_ref
    path = endpoint_publication_path(project_path)
    for _attempt in range(READ_ATTEMPTS):
        try:
            with path.open("r", encoding="utf-8") as handle:
                raw = handle.read()
        except FileNotFoundError:
            return None
        except OSError:
            # Denied while the Editor replaced it. The next attempt sees either the
            # previous complete content or the new complete content -- never a torn
            # one, which is what makes the retry safe rather than a guess.
            time_ref.sleep(READ_RETRY_SECONDS)
            continue
        try:
            return _coerce_publication(json.loads(raw))
        except ValueError:
            return None
    return None


def _normalized_path(value):
    """Normalize for comparison across case, separators, and Windows short names.

    ``realpath`` is what resolves a 8.3 short name, so a platform-default log
    cannot escape its classification by spelling.
    """
    if not value:
        return ""
    try:
        resolved = os.path.realpath(str(value))
    except OSError:
        resolved = str(value)
    return os.path.normcase(os.path.normpath(resolved))


def paths_equal(left, right):
    return bool(left) and bool(right) and _normalized_path(left) == _normalized_path(right)


def confirm_publication(publication, probe_health_fn, health_timeout_seconds):
    """Check the publication against the service it names.

    A present publication is a claim, not a conclusion. ``Temp/UnityPuerExec/``
    survives a kill, so a human can reopen the same project from Unity Hub without
    opting in and leave a stale publication next to a lockfile held by a different,
    uncontrolled process. A recycled port must not be able to impersonate a
    controlled session, for the same reason a recycled pid must not.

    The session marker is the discriminator: it is minted fresh every time the
    service starts, so a different service answering the published port cannot
    match it. The marker is present in a ``compiling`` payload as well as a ready
    one, which is what lets a mid-compile Editor confirm; ``unity_pid`` and
    ``project_path`` appear only once ready, so they are checked only then.

    Returns ``(verdict, payload)`` where verdict is one of ``"confirmed"``,
    ``"mismatched"``, or ``"unanswered"``.
    """
    payload, _error = probe_health_fn(publication["base_url"], health_timeout_seconds)
    if payload is None:
        return "unanswered", None
    if payload.get("session_marker") != publication["session_marker"]:
        return "mismatched", payload
    if payload.get("status") == "ready":
        if payload.get("unity_pid") not in (None, publication["unity_pid"]):
            return "mismatched", payload
        reported_project = payload.get("project_path")
        if reported_project and not paths_equal(reported_project, publication["project_path"]):
            return "mismatched", payload
    return "confirmed", payload


def classify_session_state(
    project_path,
    lockfile_held_fn,
    read_publication_fn,
    probe_health_fn,
    health_timeout_seconds,
    is_pid_running_fn,
    grace_seconds=SERVICE_RESTART_GRACE_SECONDS,
    time_ref=None,
):
    """Resolve the D2 table, allowing for a service that is restarting.

    The restart window is the awkward part. The service stops on every domain
    reload while the publication stays in place, so "the published port does not
    answer" describes both a controlled Editor mid-compile and residue from an
    Editor that was killed. Concluding "did not opt in" from the first unanswered
    probe would make every script compile look like a withdrawn opt-in.

    Two things separate them. First a grace window, for the ordinary case where the
    listener is down for a moment. Then, if it is still unanswered, whether the
    process the Editor published is itself still running: a live published process
    holding a held lockfile is a controlled Editor whose service is restarting, and
    the caller's existing readiness wait is the right place to wait for it. A
    published process that is gone, with the lockfile held by something else, is
    residue sitting next to an Editor that never opted in.

    The published pid is safe to consult here in a way the removed artifact's pid
    was not: the Editor stated it about itself, and it is only ever corroboration
    alongside the project's own lockfile, never the sole evidence that a session is
    live. A recycled pid therefore cannot resurrect an ended session -- that needs
    the lockfile too.

    Returns ``(state, publication, health_payload)``.
    """
    time_ref = time_module if time_ref is None else time_ref
    deadline = time_ref.time() + max(0.0, grace_seconds)

    while True:
        lockfile_held = lockfile_held_fn(project_path)
        publication = read_publication_fn(project_path)

        if publication is None:
            if not lockfile_held:
                return SESSION_STATE_NO_EDITOR, None, None
            # Held with nothing published. Still inside the grace window this may be
            # a publication being replaced; past it, the Editor did not opt in.
            if time_ref.time() >= deadline:
                return SESSION_STATE_NOT_UNDER_CONTROL, None, None
            time_ref.sleep(READ_RETRY_SECONDS)
            continue

        if not lockfile_held:
            # Published but nothing holds the project: the Editor crashed or was
            # killed. The session is over, and the published console log path stays
            # readable for post-mortem observation.
            return SESSION_STATE_ENDED_RESIDUE, publication, None

        verdict, payload = confirm_publication(publication, probe_health_fn, health_timeout_seconds)
        if verdict == "confirmed":
            return SESSION_STATE_CONTROLLED, publication, payload
        if verdict == "mismatched":
            # Something else owns the published port. Whatever holds the lockfile is
            # not reachable through this publication, so it is not under CLI control.
            return SESSION_STATE_NOT_UNDER_CONTROL, publication, payload
        if time_ref.time() < deadline:
            time_ref.sleep(READ_RETRY_SECONDS)
            continue
        if is_pid_running_fn(publication["unity_pid"]):
            return SESSION_STATE_CONTROLLED, publication, None
        return SESSION_STATE_NOT_UNDER_CONTROL, publication, None


def classify_observation_reliability(
    console_log_path,
    project_private_log_path,
    default_editor_log_path,
    other_unity_process_count=0,
):
    """Say how safe byte-offset observation of this session is, before it is taken.

    The previous change reports offset invalidation after it happens; this reports
    the hazard before a caller commits to offsets. The two are the same problem at
    opposite ends.

    Counting every Unity process on the machine is deliberate and is not the
    defect this change removes: "who else can write this per-user file" is a
    machine-wide question, unlike "which Editor serves this project".
    """
    if not console_log_path:
        return None
    if paths_equal(console_log_path, project_private_log_path):
        return OBSERVATION_PROJECT_PRIVATE
    if not paths_equal(console_log_path, default_editor_log_path):
        # Not the project-private location and not the platform guess, so it is
        # somewhere a caller named at launch. Reliable, and reliable for a reason
        # worth attributing to the caller rather than to the platform.
        return OBSERVATION_CALLER_DIRECTED
    if other_unity_process_count > 0:
        return OBSERVATION_PLATFORM_DEFAULT_CONTENDED
    return OBSERVATION_PLATFORM_DEFAULT_SOLE_EDITOR


def observation_is_reliable(classification):
    return classification in (
        OBSERVATION_PROJECT_PRIVATE,
        OBSERVATION_CALLER_DIRECTED,
        OBSERVATION_PLATFORM_DEFAULT_SOLE_EDITOR,
    )
