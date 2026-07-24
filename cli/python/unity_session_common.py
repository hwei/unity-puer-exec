#!/usr/bin/env python3
from pathlib import Path


UNITY_PROJECT_PATH_ENV = "UNITY_PROJECT_PATH"
ENV_FILE_NAME = ".env"
DEFAULT_READY_TIMEOUT_SECONDS = 180.0
DEFAULT_HEALTH_TIMEOUT_SECONDS = 2.0
DEFAULT_ACTIVITY_TIMEOUT_SECONDS = 20.0
# Bounded window in which wait-for-compile waits for `compiling` to appear after a
# refresh before concluding that no compilation was triggered. Kept short so the
# "nothing changed" path does not stall, but long enough to absorb async compile start.
DEFAULT_COMPILE_APPEAR_TIMEOUT_SECONDS = 10.0
# Short poll cadence during the appear window so a fast compile edge is not missed
# between two polls (see compile-loop-tooling design risk note).
COMPILE_APPEAR_POLL_INTERVAL_SECONDS = 0.25
DEFAULT_EDITOR_LOG_MAX_LINES = 40
DEFAULT_STOP_TIMEOUT_SECONDS = 10.0
POLL_INTERVAL_SECONDS = 1.0
RECOVERABLE_HEALTH_STATUSES = ("compiling", "not_available")
# Asks the Unity bridge to start its control service for the whole process. Unity
# passes unrecognised switches through to Environment.GetCommandLineArgs(), so the
# Editor reads it without any persistence of its own. Must match
# UnityPuerExecActivation.ActivationSwitch on the Editor side.
CONTROL_ACTIVATION_SWITCH = "-unityPuerExecControl"
# Where the Editor publishes what it is and how to reach it. Read-only from the
# CLI's side: the Editor is the only author, because every field is about the
# Editor and only the Editor can state them without guessing.
ENDPOINT_RELATIVE_PATH = Path("Temp") / "UnityPuerExec" / "endpoint.json"
LAUNCH_CLAIM_RELATIVE_PATH = Path("Temp") / "UnityPuerExec" / "launch_claim.json"
PENDING_EXEC_DIR_RELATIVE_PATH = Path("Temp") / "UnityPuerExec" / "pending_exec"
UNITY_LOCKFILE_RELATIVE_PATH = Path("Temp") / "UnityLockfile"
PROJECT_RECOVERY_WINDOW_SECONDS = 30.0
# How long a held lockfile with no answering published service is allowed to be a
# service restarting across a domain reload rather than an Editor that never opted
# in. Short, because it is only the first discriminator: a longer compile is
# separated from residue by whether the published process is still running.
SERVICE_RESTART_GRACE_SECONDS = 2.0
PENDING_EXEC_SCHEMA_VERSION = 2
PENDING_EXEC_RETENTION_MS = 24 * 60 * 60 * 1000


class UnitySessionError(Exception):
    def __init__(self, message, session=None):
        super().__init__(message)
        self.session = session


class UnityLaunchError(UnitySessionError):
    pass


class UnityLaunchConflictError(UnitySessionError):
    pass


class UnityNotReadyError(UnitySessionError):
    pass


class UnityStalledError(UnitySessionError):
    pass


class UnityVersionMismatchError(UnitySessionError):
    """Raised when an owned control endpoint reports a version the CLI cannot match.

    Carried out of the session layer so the refusal happens at the moment the
    disagreement first becomes observable, before the command performs work.
    """

    def __init__(self, detail, message=None, session=None):
        super().__init__(message or "version mismatch", session=session)
        self.detail = detail


class UnitySessionStateError(UnitySessionError):
    def __init__(self, status, message, session=None):
        super().__init__(message, session=session)
        self.status = status


class UnityEditorNotUnderControlError(UnitySessionStateError):
    """An Editor is serving the project, but it never activated a control service.

    Its own status and exit code because the remedy is an activation decision, not
    a retry: it is neither a failure to launch nor a failure to become ready, and a
    caller that cannot tell those apart will retry something that cannot succeed.

    Replaces the previous behaviour of silently attaching to whatever answered the
    preferred control port -- which only appeared to work when exactly one Editor
    was open, and misattributed the session to an unrelated project when it was not.
    """

    STATUS = "editor_not_under_cli_control"

    def __init__(self, message, session=None, guidance=None):
        super().__init__(self.STATUS, message, session=session)
        self.guidance = guidance or []


class UnitySession:
    def __init__(
        self,
        owner,
        base_url,
        project_path,
        unity_pid=None,
        unity_exe_path=None,
        launched=False,
        process=None,
        effective_log_path=None,
    ):
        self.owner = owner
        self.base_url = base_url.rstrip("/")
        self.project_path = str(project_path)
        self.unity_pid = unity_pid
        self.unity_exe_path = unity_exe_path
        self.launched = launched
        self.process = process
        self.effective_log_path = str(effective_log_path) if effective_log_path else None
        self.diagnostics = {}

    def to_payload(self):
        payload = {
            "owner": self.owner,
            "launched": self.launched,
            "base_url": self.base_url,
            "project_path": self.project_path,
        }
        if self.unity_pid is not None:
            payload["unity_pid"] = self.unity_pid
        if self.unity_exe_path:
            payload["unity_exe_path"] = self.unity_exe_path
        return payload
