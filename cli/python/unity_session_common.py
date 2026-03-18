#!/usr/bin/env python3
from pathlib import Path


UNITY_PROJECT_PATH_ENV = "UNITY_PROJECT_PATH"
ENV_FILE_NAME = ".env"
DEFAULT_READY_TIMEOUT_SECONDS = 180.0
DEFAULT_HEALTH_TIMEOUT_SECONDS = 2.0
DEFAULT_ACTIVITY_TIMEOUT_SECONDS = 20.0
DEFAULT_EDITOR_LOG_MAX_LINES = 40
DEFAULT_STOP_TIMEOUT_SECONDS = 10.0
POLL_INTERVAL_SECONDS = 1.0
RECOVERABLE_HEALTH_STATUSES = ("compiling", "not_available")
SESSION_RELATIVE_PATH = Path("Temp") / "UnityPuerExec" / "session.json"
LAUNCH_CLAIM_RELATIVE_PATH = Path("Temp") / "UnityPuerExec" / "launch_claim.json"
UNITY_LOCKFILE_RELATIVE_PATH = Path("Temp") / "UnityLockfile"
PROJECT_RECOVERY_WINDOW_SECONDS = 30.0


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


class UnitySessionStateError(UnitySessionError):
    def __init__(self, status, message, session=None):
        super().__init__(message, session=session)
        self.status = status


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
