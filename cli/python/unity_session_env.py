#!/usr/bin/env python3
import json
import os
from pathlib import Path

from unity_session_common import ENV_FILE_NAME, UNITY_PROJECT_PATH_ENV


_PACKAGE_ID = "com.txcombo.unity-puer-exec"


def _infer_project_from_exe(argv0):
    if not argv0:
        return None
    exe_path = Path(argv0).resolve()
    for parent in exe_path.parents:
        manifest = parent / "Packages" / "manifest.json"
        if manifest.exists():
            try:
                with manifest.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                if _PACKAGE_ID in data.get("dependencies", {}):
                    return parent
            except Exception:
                pass
    return None


_DOTENV_LOADED = False


def repo_root(module_file):
    return Path(module_file).resolve().parents[2]


def dotenv_path(module_file, repo_root_path=None):
    repo_root_path = repo_root(module_file) if repo_root_path is None else Path(repo_root_path)
    return repo_root_path / ENV_FILE_NAME


def load_dotenv_file(dotenv_file, env=None):
    env = os.environ if env is None else env
    dotenv_file = Path(dotenv_file)
    if not dotenv_file.exists():
        return False

    with dotenv_file.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if key and key not in env:
                env[key] = value
    return True


def ensure_dotenv_loaded(module_file, env=None, dotenv_file=None, force=False):
    global _DOTENV_LOADED

    env = os.environ if env is None else env
    if _DOTENV_LOADED and not force and dotenv_file is None and env is os.environ:
        return False

    loaded = load_dotenv_file(dotenv_path(module_file) if dotenv_file is None else dotenv_file, env=env)
    if env is os.environ and dotenv_file is None:
        _DOTENV_LOADED = True
    return loaded


def resolve_project_path(module_file, project_path=None, cwd=None, env=None, ensure_dotenv_loaded_fn=None, argv0=None):
    if project_path:
        return Path(project_path)

    env = os.environ if env is None else env
    if ensure_dotenv_loaded_fn is not None:
        ensure_dotenv_loaded_fn(env=env)
    else:
        ensure_dotenv_loaded(module_file, env=env)
    env_project_path = env.get(UNITY_PROJECT_PATH_ENV)
    if env_project_path:
        return Path(env_project_path)

    if argv0 is not None:
        inferred = _infer_project_from_exe(argv0)
        if inferred is not None:
            return inferred

    return Path.cwd() if cwd is None else Path(cwd)
