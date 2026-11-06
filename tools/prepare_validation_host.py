import argparse
import datetime
import hashlib
import json
import os
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
UNITY_PROJECT_PATH_ENV = "UNITY_PROJECT_PATH"
FORMAL_PACKAGE_NAME = "com.txcombo.unity-puer-exec"
LEGACY_PACKAGE_NAME = "com.c3.unity-puer-exec.validation"
FORMAL_PACKAGE_ROOT = REPO_ROOT / "packages" / FORMAL_PACKAGE_NAME

# The host-local backup convention an operator following the run instructions by
# hand already produces, so an existing skeleton is recognizable rather than
# competed with. The dated child keeps a same-day repeat from colliding.
EMBEDDED_SHADOW_BACKUP_DIR_NAME = ".unity-puer-exec-embedded-backup"
BACKUP_ENTRY_NAME_PATTERN = re.compile(r"^(?P<directory_name>.+)-\d{8}$")
# The manifest backup is a sibling of the shadow backup on purpose: the shadow
# operations treat every child of their root as a moved package directory, so a
# shared root would make two independent undo records compete for one namespace.
MANIFEST_BACKUP_DIR_NAME = ".unity-puer-exec-manifest-backup"
MANIFEST_BACKUP_MANIFEST_NAME = "manifest.json"
MANIFEST_BACKUP_LOCKFILE_NAME = "packages-lock.json"
WRITTEN_MANIFEST_HASH_NAME = "written-manifest.sha256"
PACKAGES_LOCKFILE_NAME = "packages-lock.json"
# The project-local state the real-host suite decides host freedom from.
UNITY_LOCKFILE_RELATIVE_PATH = Path("Temp") / "UnityLockfile"
ENDPOINT_PUBLICATION_RELATIVE_PATH = Path("Temp") / "UnityPuerExec" / "endpoint.json"

STATUS_CLEARED = "cleared"
STATUS_RESTORED = "restored"
STATUS_UNCHANGED = "unchanged"
STATUS_REFUSED = "refused"
STATUS_DRY_RUN = "dry-run"
STATUS_UPDATED = "updated"

# A refusal is a named answer, not a pass: exit zero would let a shell `&&` chain
# run a real-host suite against a host the tool declined to touch.
EXIT_REFUSED = 2

try:
    import msvcrt
except ImportError:  # pragma: no cover - the validation host is a Windows tool.
    msvcrt = None


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


def resolve_project_path(project_path=None, env=None, dotenv_path=None):
    target_env = os.environ if env is None else env
    _load_dotenv_path(target_env, REPO_ROOT / ".env" if dotenv_path is None else Path(dotenv_path))

    if project_path:
        return Path(project_path).resolve()

    env_project_path = target_env.get(UNITY_PROJECT_PATH_ENV)
    if env_project_path:
        return Path(env_project_path).resolve()

    raise ValueError(
        "Validation host project path is required. Pass --project-path or set {}.".format(
            UNITY_PROJECT_PATH_ENV
        )
    )


def project_path_to_manifest_path(project_path):
    return project_path / "Packages" / "manifest.json"


def _resolved_path(path):
    try:
        return path.resolve()
    except OSError:
        return path.absolute()


def _declares_formal_package_name(candidate_path):
    package_json_path = candidate_path / "package.json"
    try:
        package_data = json.loads(package_json_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    if not isinstance(package_data, dict):
        return False
    return package_data.get("name") == FORMAL_PACKAGE_NAME


def detect_embedded_package_shadowing(manifest_path, package_root=None):
    """Report directories under Packages/ that Unity would load as the formal package.

    Unity identifies an embedded package by the ``name`` declared in its
    ``package.json``, not by the directory name, so the scan reads candidate
    manifests rather than testing one fixed path.
    """
    package_root = FORMAL_PACKAGE_ROOT if package_root is None else Path(package_root)
    packages_path = Path(manifest_path).parent
    if not packages_path.is_dir():
        return False, None, []

    package_root_resolved = _resolved_path(package_root)
    shadowing_paths = []

    for candidate_path in sorted(packages_path.iterdir()):
        if not candidate_path.is_dir():
            continue
        if not _declares_formal_package_name(candidate_path):
            continue
        if _resolved_path(candidate_path) == package_root_resolved:
            continue
        shadowing_paths.append(str(candidate_path))

    if not shadowing_paths:
        return False, None, []

    return True, shadowing_paths[0], shadowing_paths


def project_path_for_manifest(manifest_path):
    """The host project root a manifest belongs to (``<host>/Packages/manifest.json``)."""
    return Path(manifest_path).resolve().parent.parent


def embedded_shadow_backup_root(project_path):
    return Path(project_path) / EMBEDDED_SHADOW_BACKUP_DIR_NAME


def manifest_backup_root(project_path):
    return Path(project_path) / MANIFEST_BACKUP_DIR_NAME


def project_lockfile_is_held(project_path):
    """Whether some Editor currently holds the project's Unity lockfile.

    Mirrors ``unity_session_process._project_lockfile_is_held``, the rule the
    real-host suite's clean-boundary check delegates to: a lockfile that merely
    exists is not evidence of a live Editor, because Windows leaves the file on
    disk after the Editor exits. Only a lock that cannot be taken -- the file
    cannot be opened, or an exclusive byte lock is already held -- means busy.
    The check reads project-local state only; it never lists machine-wide
    processes and never stops anything.
    """
    lockfile_path = Path(project_path) / UNITY_LOCKFILE_RELATIVE_PATH
    try:
        descriptor = os.open(str(lockfile_path), os.O_RDWR)
    except FileNotFoundError:
        return False
    except OSError:
        # Present but denied: another handle owns it, which is the busy signal.
        return True
    try:
        if msvcrt is None:  # pragma: no cover - conservative fallback off Windows.
            return True
        try:
            msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
        except OSError:
            return True
        msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
        return False
    finally:
        os.close(descriptor)


def read_editor_endpoint_publication(project_path):
    """The Editor's own published endpoint record, or ``None``.

    Only a record complete enough to act on is returned: the same rule
    ``unity_session_endpoint._coerce_publication`` applies, because a half-filled
    publication is not an answer about a live Editor.
    """
    endpoint_path = Path(project_path) / ENDPOINT_PUBLICATION_RELATIVE_PATH
    try:
        payload = json.loads(endpoint_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    port = payload.get("port")
    unity_pid = payload.get("unity_pid")
    project_path_value = payload.get("project_path")
    session_marker = payload.get("session_marker")
    if not isinstance(port, int) or isinstance(port, bool) or port <= 0:
        return None
    if not isinstance(unity_pid, int) or isinstance(unity_pid, bool) or unity_pid <= 0:
        return None
    if not isinstance(project_path_value, str) or not project_path_value:
        return None
    if not isinstance(session_marker, str) or not session_marker:
        return None
    return payload


def editor_endpoint_is_live(project_path, is_pid_running_fn=None):
    """Whether a published endpoint still names a running Editor process.

    A publication that merely exists is not evidence of a live Editor: the CLI's
    own state table calls that combination (publication present, lockfile free)
    ``ended_residue`` -- the file outlives a crashed or killed Editor, and the
    real-host suite leaves one behind after every run. Following the suite's
    classification, the published process is what distinguishes a live session
    from residue, so this corroborates instead of trusting presence.
    """
    publication = read_editor_endpoint_publication(project_path)
    if publication is None:
        return False
    is_pid_running_fn = _pid_is_running if is_pid_running_fn is None else is_pid_running_fn
    return bool(is_pid_running_fn(publication["unity_pid"]))


def _pid_is_running(pid):
    """Whether ``pid`` exists, using the same probe the session CLI uses.

    The session CLI owns the one definition of "is this pid alive", so this reuses
    it rather than growing a second process probe. The import stays local so merely
    importing this module does not change another tool's import environment.
    """
    if pid is None:
        return False
    cli_python_dir = REPO_ROOT / "cli" / "python"
    if str(cli_python_dir) not in sys.path:
        sys.path.insert(0, str(cli_python_dir))
    try:
        import unity_session_process  # type: ignore
    except Exception:  # noqa: BLE001 - absence must not read as "free".
        # Cannot confirm the published process is gone, so treat the host as busy:
        # refusing is the safe direction for a move of tracked files.
        return True
    return unity_session_process.is_pid_running(pid)


def host_freedom_refusal(project_path, lockfile_held_fn=None, endpoint_live_fn=None):
    """Return a named refusal reason when the host is not free, else ``None``.

    Moving a package out of (or back into) ``Packages/`` while an Editor serves the
    project leaves its asset database describing a package that is no longer there,
    so both directions refuse. This is a check, not a kill: the tool never stops an
    Editor process.
    """
    lockfile_held_fn = project_lockfile_is_held if lockfile_held_fn is None else lockfile_held_fn
    endpoint_live_fn = editor_endpoint_is_live if endpoint_live_fn is None else endpoint_live_fn
    if lockfile_held_fn(project_path):
        return "host_not_free: the project's Unity lockfile is held ({})".format(
            Path(project_path) / UNITY_LOCKFILE_RELATIVE_PATH
        )
    if endpoint_live_fn(project_path):
        return (
            "host_not_free: an Editor is serving this project through its published "
            "control endpoint ({})"
        ).format(Path(project_path) / ENDPOINT_PUBLICATION_RELATIVE_PATH)
    return None


def _backup_date_suffix(today=None):
    today = datetime.date.today() if today is None else today
    return today.strftime("%Y%m%d")


def _move_path(source, target):
    """Rename one directory, never replacing a path that already exists."""
    os.rename(str(source), str(target))


def _remove_empty_directory(path):
    """Remove a directory only when it is empty; never removes content.

    Two cases need this. An empty dated directory left at the backup path by an
    earlier hand-rolled clear is inert skeleton, not occupied backup, so a clear may
    reuse it. And once a restore has moved everything back, the backup root this tool
    created is empty; leaving it behind would make the host's version-control status
    differ from what it was before the clear.
    """
    try:
        next(iter(Path(path).iterdir()))
    except StopIteration:
        os.rmdir(str(path))
        return True
    except OSError:
        return False
    return False


def _move_all_with_rollback(planned_moves):
    """Move each (source, target) pair, undoing completed moves if one fails.

    A filesystem move is not transactional, and a half-cleared host is worse than
    an untouched one: compensating moves put back what this call already moved, so
    a failure leaves the host as it was found. Nothing is ever deleted.
    """
    completed = []
    try:
        for source, target in planned_moves:
            _move_path(source, target)
            completed.append({"source": str(source), "target": str(target)})
    except OSError as exc:
        rolled_back = 0
        for move in reversed(completed):
            try:
                _move_path(Path(move["target"]), Path(move["source"]))
                rolled_back += 1
            except OSError:
                pass
        return None, "move_failed: {} ({} of {} moves rolled back)".format(
            exc, rolled_back, len(completed)
        )
    return completed, None


def _outcome(status, backup_path=None, reason=None, moved=None, left_in_place=None):
    outcome = {
        "status": status,
        "backup_path": None if backup_path is None else str(backup_path),
        "reason": reason,
        "moved": list(moved or []),
    }
    if left_in_place is not None:
        outcome["left_in_place"] = list(left_in_place)
    return outcome


def clear_embedded_shadow(
    project_path,
    manifest_path=None,
    dry_run=False,
    package_root=None,
    today=None,
    lockfile_held_fn=None,
    endpoint_live_fn=None,
):
    """Move every shadowing ``Packages/`` child into the host-local backup.

    Idempotent (an already-clear host reports ``unchanged``), never deletes, and
    refuses -- naming the occupied path -- rather than nesting into or overwriting a
    backup left behind by an earlier clear that was never restored.
    """
    project_path = Path(project_path)
    manifest_path = (
        project_path_to_manifest_path(project_path)
        if manifest_path is None
        else Path(manifest_path)
    )
    backup_root = embedded_shadow_backup_root(project_path)

    _shadowing, _first, shadowing_paths = detect_embedded_package_shadowing(
        manifest_path, package_root=package_root
    )
    if not shadowing_paths:
        return _outcome(STATUS_UNCHANGED)

    refusal = host_freedom_refusal(
        project_path,
        lockfile_held_fn=lockfile_held_fn,
        endpoint_live_fn=endpoint_live_fn,
    )
    if refusal:
        return _outcome(STATUS_REFUSED, reason=refusal)

    if backup_root.exists() and not backup_root.is_dir():
        return _outcome(
            STATUS_REFUSED,
            backup_path=backup_root,
            reason="backup_root_not_a_directory: {}".format(backup_root),
        )

    date_suffix = _backup_date_suffix(today)
    planned_moves = []
    reusable_skeletons = []
    for shadowing_path in shadowing_paths:
        source = Path(shadowing_path)
        target = backup_root / "{}-{}".format(source.name, date_suffix)
        if target.exists():
            # An empty directory is inert skeleton from a hand-rolled clear, not an
            # occupied backup. It is only *recorded* here so the preview stays
            # write-free; the action below re-checks before reusing it.
            if target.is_dir() and not any(target.iterdir()):
                reusable_skeletons.append(target)
            else:
                return _outcome(
                    STATUS_REFUSED,
                    backup_path=backup_root,
                    reason=(
                        "backup_path_occupied: {} already holds content from an earlier clear"
                    ).format(target),
                )
        planned_moves.append((source, target))

    if dry_run:
        return _outcome(
            STATUS_DRY_RUN,
            backup_path=backup_root,
            moved=[{"source": str(s), "target": str(t)} for s, t in planned_moves],
        )

    try:
        backup_root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return _outcome(
            STATUS_REFUSED,
            backup_path=backup_root,
            reason="backup_root_unwritable: {} ({})".format(backup_root, exc),
        )
    for skeleton in reusable_skeletons:
        # Re-check: content may have appeared between planning and acting, and this
        # refuses rather than removing anything that holds a file.
        if not _remove_empty_directory(skeleton):
            return _outcome(
                STATUS_REFUSED,
                backup_path=backup_root,
                reason=(
                    "backup_path_occupied: {} already holds content from an earlier clear"
                ).format(skeleton),
            )
    moved, failure = _move_all_with_rollback(planned_moves)
    if failure is not None:
        _remove_empty_directory(backup_root)
        return _outcome(STATUS_REFUSED, backup_path=backup_root, reason=failure)
    return _outcome(STATUS_CLEARED, backup_path=backup_root, moved=moved)


def restore_embedded_shadow(
    project_path,
    manifest_path=None,
    dry_run=False,
    today=None,
    lockfile_held_fn=None,
    endpoint_live_fn=None,
):
    """Move the backup's contents back to their original ``Packages/`` paths.

    Driven by what the backup actually holds (design D3): clear records each moved
    directory as ``<directory name>-<YYYYMMDD>``, so the dated suffix is stripped to
    recover the original child name. It never merges and never overwrites -- an
    occupied target refuses and names itself. An empty dated directory is the inert
    skeleton a hand-rolled clear leaves behind; it holds nothing, so there is
    nothing to restore and it is skipped rather than treated as an error.
    """
    project_path = Path(project_path)
    manifest_path = (
        project_path_to_manifest_path(project_path)
        if manifest_path is None
        else Path(manifest_path)
    )
    packages_path = Path(manifest_path).parent
    backup_root = embedded_shadow_backup_root(project_path)

    if not backup_root.is_dir():
        return _outcome(STATUS_UNCHANGED)
    entries = sorted(backup_root.iterdir())
    if not entries:
        return _outcome(STATUS_UNCHANGED, backup_path=backup_root)

    refusal = host_freedom_refusal(
        project_path,
        lockfile_held_fn=lockfile_held_fn,
        endpoint_live_fn=endpoint_live_fn,
    )
    if refusal:
        return _outcome(STATUS_REFUSED, backup_path=backup_root, reason=refusal)

    planned_moves = []
    for entry in entries:
        if not entry.is_dir():
            return _outcome(
                STATUS_REFUSED,
                backup_path=backup_root,
                reason="backup_entry_unrecognized: {} is not a directory".format(entry),
            )
        if not any(entry.iterdir()):
            # Inert skeleton: holds nothing, so there is nothing to restore.
            continue
        if not _declares_formal_package_name(entry):
            return _outcome(
                STATUS_REFUSED,
                backup_path=backup_root,
                reason="backup_entry_not_embedded_package: {} declares no {}".format(
                    entry, FORMAL_PACKAGE_NAME
                ),
            )
        match = BACKUP_ENTRY_NAME_PATTERN.match(entry.name)
        if match is None:
            return _outcome(
                STATUS_REFUSED,
                backup_path=backup_root,
                reason="backup_entry_unrecognized: {} carries no -YYYYMMDD suffix".format(entry),
            )
        target = packages_path / match.group("directory_name")
        if target.exists():
            return _outcome(
                STATUS_REFUSED,
                backup_path=backup_root,
                reason=(
                    "restore_target_occupied: {} already exists; refusing to merge or overwrite"
                ).format(target),
            )
        planned_moves.append((entry, target))

    if not planned_moves:
        return _outcome(STATUS_UNCHANGED, backup_path=backup_root)

    if dry_run:
        return _outcome(
            STATUS_DRY_RUN,
            backup_path=backup_root,
            moved=[{"source": str(s), "target": str(t)} for s, t in planned_moves],
        )

    moved, failure = _move_all_with_rollback(planned_moves)
    if failure is not None:
        return _outcome(STATUS_REFUSED, backup_path=backup_root, reason=failure)
    # The inverse has to be exact, including the directory tree: an empty backup
    # left at the host root would make the host's version-control status differ from
    # what it was before the clear. Only empty directories go; nothing is deleted.
    _remove_empty_directory(backup_root)
    return _outcome(STATUS_RESTORED, backup_path=backup_root, moved=moved)


def _sha256_of_file(path):
    digest = hashlib.sha256()
    digest.update(Path(path).read_bytes())
    return digest.hexdigest()


def save_manifest_backup(manifest_path, project_path=None):
    """Record the pre-preparation originals before the first manifest rewrite.

    The originals are saved exactly once: a later rewrite (say one that only adds
    ``testables``) must leave the saved files alone, because those still describe
    the host as it was before preparation touched it. ``packages-lock.json`` is
    saved only when the host had one; its absence is what tells the restore to
    leave Unity's regenerated lock file in place rather than deleting it.

    Returns ``(backup_root, reason)``; ``reason`` names why nothing could be saved.
    """
    manifest_path = Path(manifest_path)
    project_path = (
        project_path_for_manifest(manifest_path) if project_path is None else Path(project_path)
    )
    backup_root = manifest_backup_root(project_path)

    try:
        if backup_root.exists() and not backup_root.is_dir():
            return backup_root, "manifest_backup_unusable: {} is not a directory".format(
                backup_root
            )
        backup_root.mkdir(parents=True, exist_ok=True)
        saved_manifest = backup_root / MANIFEST_BACKUP_MANIFEST_NAME
        if not saved_manifest.exists():
            # Write beside the destination and rename, so an interrupted copy can
            # never leave a truncated "original" that a later restore would trust.
            staging_path = backup_root / (MANIFEST_BACKUP_MANIFEST_NAME + ".partial")
            staging_path.write_bytes(manifest_path.read_bytes())
            os.replace(str(staging_path), str(saved_manifest))
            lockfile_source = manifest_path.parent / PACKAGES_LOCKFILE_NAME
            if lockfile_source.is_file():
                lockfile_staging = backup_root / (MANIFEST_BACKUP_LOCKFILE_NAME + ".partial")
                lockfile_staging.write_bytes(lockfile_source.read_bytes())
                os.replace(
                    str(lockfile_staging), str(backup_root / MANIFEST_BACKUP_LOCKFILE_NAME)
                )
    except OSError as exc:
        return backup_root, "manifest_backup_unwritable: {} ({})".format(backup_root, exc)
    return backup_root, None


def record_written_manifest_hash(backup_root, manifest_path):
    """Record the hash of the content preparation just wrote.

    The restore compares the current manifest against this value to notice an edit
    made after preparation. It is rewritten on every real write, because the point
    of comparison is the latest content this tool produced.

    Returns ``None`` on success, else a named refusal reason.
    """
    hash_path = Path(backup_root) / WRITTEN_MANIFEST_HASH_NAME
    try:
        hash_path.write_text(_sha256_of_file(manifest_path) + "\n", encoding="utf-8")
    except OSError as exc:
        return "written_manifest_hash_unwritable: {} ({})".format(hash_path, exc)
    return None


def _restore_backup_files(planned_moves):
    """Replace each target with its saved original, rolling back on failure.

    A filesystem move is not transactional, so a failure part-way puts back the
    backups this call already moved. Nothing else is touched: the content a
    successful move replaced is exactly what the restore was asked to discard.
    """
    completed = []
    try:
        for source, target in planned_moves:
            os.replace(str(source), str(target))
            completed.append({"source": str(source), "target": str(target)})
    except OSError as exc:
        rolled_back = 0
        for move in reversed(completed):
            try:
                os.replace(move["target"], move["source"])
                rolled_back += 1
            except OSError:
                pass
        return None, "move_failed: {} ({} of {} files rolled back)".format(
            exc, rolled_back, len(planned_moves)
        )
    return completed, None


def restore_manifest(
    project_path,
    manifest_path=None,
    dry_run=False,
    lockfile_held_fn=None,
    endpoint_live_fn=None,
):
    """Move the host's pre-preparation manifest and lock file back into ``Packages/``.

    Follows the shadow restore's safety rules (host freedom, preview, machine
    readable outcome) plus one guard of its own: the current ``manifest.json`` must
    still hash to what preparation last wrote, so an edit made after preparation is
    never silently discarded. The lock file is deliberately unguarded -- Unity
    rewrites it on every resolve, so guarding it would block every real restore.
    """
    project_path = Path(project_path)
    manifest_path = (
        project_path_to_manifest_path(project_path)
        if manifest_path is None
        else Path(manifest_path)
    )
    packages_path = Path(manifest_path).parent
    backup_root = manifest_backup_root(project_path)
    saved_manifest = backup_root / MANIFEST_BACKUP_MANIFEST_NAME

    if not backup_root.is_dir():
        return _outcome(STATUS_UNCHANGED)
    if not saved_manifest.is_file():
        return _outcome(
            STATUS_REFUSED,
            backup_path=backup_root,
            reason="manifest_backup_unrecognized: {} holds no saved manifest".format(
                backup_root
            ),
        )

    refusal = host_freedom_refusal(
        project_path,
        lockfile_held_fn=lockfile_held_fn,
        endpoint_live_fn=endpoint_live_fn,
    )
    if refusal:
        return _outcome(STATUS_REFUSED, backup_path=backup_root, reason=refusal)

    recorded_hash_path = backup_root / WRITTEN_MANIFEST_HASH_NAME
    try:
        recorded_hash = recorded_hash_path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        return _outcome(
            STATUS_REFUSED,
            backup_path=backup_root,
            reason="written_manifest_hash_unreadable: {} ({})".format(
                recorded_hash_path, exc
            ),
        )
    try:
        current_hash = _sha256_of_file(manifest_path)
    except OSError as exc:
        return _outcome(
            STATUS_REFUSED,
            backup_path=backup_root,
            reason="manifest_unreadable: {} ({})".format(manifest_path, exc),
        )
    if current_hash != recorded_hash:
        return _outcome(
            STATUS_REFUSED,
            backup_path=backup_root,
            reason=(
                "manifest_modified_since_prepare: {} no longer matches the content "
                "preparation wrote (recorded in {})"
            ).format(manifest_path, recorded_hash_path),
        )

    planned_moves = [(saved_manifest, manifest_path)]
    saved_lockfile = backup_root / MANIFEST_BACKUP_LOCKFILE_NAME
    if saved_lockfile.is_file():
        planned_moves.append((saved_lockfile, packages_path / PACKAGES_LOCKFILE_NAME))
    current_lockfile = packages_path / PACKAGES_LOCKFILE_NAME
    # A lock file the host did not have before preparation cannot be removed -- the
    # tool never deletes host files -- so the regenerated one stays and is reported.
    left_in_place = (
        [str(current_lockfile)]
        if not saved_lockfile.is_file() and current_lockfile.exists()
        else []
    )

    if dry_run:
        return _outcome(
            STATUS_DRY_RUN,
            backup_path=backup_root,
            moved=[{"source": str(s), "target": str(t)} for s, t in planned_moves],
            left_in_place=left_in_place,
        )

    moved, failure = _restore_backup_files(planned_moves)
    if failure is not None:
        return _outcome(STATUS_REFUSED, backup_path=backup_root, reason=failure)
    # Only tool-owned metadata goes: the recorded hash and then the empty root. The
    # host's restored files are in place, so its version-control status matches the
    # pre-preparation state for those paths.
    try:
        if recorded_hash_path.exists():
            os.unlink(str(recorded_hash_path))
    except OSError:
        pass
    _remove_empty_directory(backup_root)
    return _outcome(
        STATUS_RESTORED,
        backup_path=backup_root,
        moved=moved,
        left_in_place=left_in_place,
    )


def _normalized_anchor(path):
    return str(path.anchor).rstrip("\\/").lower()


def _absolute_file_dependency(package_root):
    normalized = package_root.as_posix().lstrip("/")
    return "file:///{}".format(normalized)


def compute_file_dependency(manifest_path, package_root=None):
    package_root = FORMAL_PACKAGE_ROOT if package_root is None else Path(package_root)
    manifest_parent = Path(manifest_path).parent
    if _normalized_anchor(package_root) == _normalized_anchor(manifest_parent):
        relative_path = os.path.relpath(package_root, manifest_parent)
        return "file:{}".format(relative_path.replace("\\", "/"))
    return _absolute_file_dependency(package_root)


def ensure_testable_package(manifest_data, package_name=FORMAL_PACKAGE_NAME):
    """Declare the formal package in the manifest's ``testables`` list.

    Unity compiles and discovers a package's own test assemblies only when the
    package name is listed in ``testables``. The package's EditMode harness lives
    inside the package, so a host wired to that harness has to declare it: without
    the entry a ``-runTests`` launch exits successfully having run nothing, which
    reads as a pass. Existing unrelated entries are preserved.

    Returns the (possibly rewritten) manifest and whether it changed.
    """
    testables = manifest_data.get("testables")
    if testables is None:
        testables = []
    elif not isinstance(testables, list):
        raise ValueError("manifest.json testables must be a list when present.")

    if package_name in testables:
        return manifest_data, False

    rewritten_manifest = dict(manifest_data)
    rewritten_manifest["testables"] = list(testables) + [package_name]
    return rewritten_manifest, True


def rewrite_manifest(manifest_data, manifest_path, package_root=None):
    dependencies = manifest_data.get("dependencies")
    if not isinstance(dependencies, dict):
        raise ValueError("manifest.json must contain a dependencies object.")

    expected_value = compute_file_dependency(manifest_path, package_root=package_root)
    current_value = dependencies.get(FORMAL_PACKAGE_NAME)
    legacy_value = dependencies.get(LEGACY_PACKAGE_NAME)

    if current_value == expected_value and LEGACY_PACKAGE_NAME not in dependencies:
        rewritten_manifest = manifest_data
        changed = False
    else:
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

    # The dependency alone wires the runtime package; the testables declaration is
    # what makes the package's EditMode harness reachable from the same host.
    rewritten_manifest, testables_changed = ensure_testable_package(rewritten_manifest)
    return rewritten_manifest, changed or testables_changed, expected_value


def write_manifest(manifest_path, manifest_data):
    manifest_path.write_text(
        json.dumps(manifest_data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def build_preparation_report(manifest_path, manifest_data):
    """The existing preparation envelope, extended with the shadow-switch fields.

    The existing keys keep their meanings, including ``embedded_package_shadowing``
    and its path list, which describe the state at the moment of the call. Every
    consumer that reads them today (the real-host skip checks, the release helper)
    therefore keeps working unchanged.
    """
    shadowing, embedded_package_path, embedded_package_paths = detect_embedded_package_shadowing(
        manifest_path
    )
    rewritten_manifest, changed, dependency_value = rewrite_manifest(manifest_data, manifest_path)
    testables = rewritten_manifest.get("testables") or []
    return (
        {
            "status": STATUS_UNCHANGED,
            "manifest_path": str(manifest_path),
            "package_name": FORMAL_PACKAGE_NAME,
            "dependency": dependency_value,
            "testables": list(testables),
            "package_testable": FORMAL_PACKAGE_NAME in testables,
            "embedded_package_shadowing": shadowing,
            "embedded_package_path": embedded_package_path,
            "embedded_package_paths": embedded_package_paths,
            "backup_path": None,
            "manifest_backup_path": str(
                manifest_backup_root(project_path_for_manifest(manifest_path))
            ),
            "reason": None,
            "moved": [],
        },
        rewritten_manifest,
        changed,
    )


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Rewrite a validation host manifest to consume the formal local Unity package, "
            "including the testables declaration its EditMode harness needs, clear or "
            "restore an embedded package that shadows it, and restore the manifest wiring "
            "from the backup the first rewrite saved."
        )
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
        help="Print what would happen without writing manifest.json or moving anything.",
    )
    shadow_group = parser.add_mutually_exclusive_group()
    shadow_group.add_argument(
        "--clear-embedded-shadow",
        action="store_true",
        help=(
            "Move every immediate Packages/ child that declares {} out of Packages/ into "
            "<host>/{}/<directory name>-<YYYYMMDD>/. Never deletes. Refuses (exit {}) "
            "while an Editor is serving the host.".format(
                FORMAL_PACKAGE_NAME, EMBEDDED_SHADOW_BACKUP_DIR_NAME, EXIT_REFUSED
            )
        ),
    )
    shadow_group.add_argument(
        "--restore-embedded-shadow",
        action="store_true",
        help=(
            "Move the directories an earlier --clear-embedded-shadow moved back to their "
            "original Packages/ paths. Never deletes. Refuses (exit {}) while an Editor is "
            "serving the host, or when a target path is already occupied.".format(EXIT_REFUSED)
        ),
    )
    shadow_group.add_argument(
        "--restore-manifest",
        action="store_true",
        help=(
            "Move the manifest.json and packages-lock.json saved by the first preparation "
            "rewrite back into Packages/, and remove the tool-owned backup. Never deletes "
            "host files. Refuses (exit {}) while an Editor is serving the host, or when "
            "manifest.json changed after preparation (manifest_modified_since_prepare).".format(
                EXIT_REFUSED
            )
        ),
    )
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.manifest_path:
        manifest_path = Path(args.manifest_path).resolve()
        if args.project_path:
            project_path = Path(args.project_path).resolve()
        else:
            # The backup lives at the host root, which for a manifest override is
            # still the manifest's grandparent (<host>/Packages/manifest.json).
            project_path = project_path_for_manifest(manifest_path)
    else:
        project_path = resolve_project_path(args.project_path)
        manifest_path = project_path_to_manifest_path(project_path)

    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))

    if args.clear_embedded_shadow or args.restore_embedded_shadow or args.restore_manifest:
        if args.clear_embedded_shadow:
            operation = clear_embedded_shadow
        elif args.restore_embedded_shadow:
            operation = restore_embedded_shadow
        else:
            operation = restore_manifest
        if manifest_path.parent.name != "Packages":
            # The backup lives next to Packages/, so a manifest that is not
            # <host>/Packages/manifest.json gives no host root to act inside.
            print(
                json.dumps(
                    {
                        "status": STATUS_REFUSED,
                        "manifest_path": str(manifest_path),
                        "package_name": FORMAL_PACKAGE_NAME,
                        "backup_path": None,
                        "reason": (
                            "manifest_not_in_packages: shadow switching needs "
                            "<host>/Packages/manifest.json, got {}"
                        ).format(manifest_path),
                        "moved": [],
                    },
                    ensure_ascii=False,
                )
            )
            return EXIT_REFUSED
        # Report fields are resolved before anything moves, so an unusable manifest
        # refuses without acting instead of failing after a move has happened. The
        # shadowing fields are then recomputed afterwards, which is what lets a
        # caller verify the clear without a second invocation.
        try:
            payload, _rewritten_manifest, _changed = build_preparation_report(
                manifest_path, manifest_data
            )
        except ValueError as exc:
            payload = {
                "status": STATUS_REFUSED,
                "manifest_path": str(manifest_path),
                "package_name": FORMAL_PACKAGE_NAME,
                "backup_path": None,
                "reason": "manifest_unusable: {}".format(exc),
                "moved": [],
            }
            print(json.dumps(payload, ensure_ascii=False))
            return EXIT_REFUSED
        outcome = operation(project_path, manifest_path=manifest_path, dry_run=args.dry_run)
        shadowing, embedded_package_path, embedded_package_paths = (
            detect_embedded_package_shadowing(manifest_path)
        )
        payload["embedded_package_shadowing"] = shadowing
        payload["embedded_package_path"] = embedded_package_path
        payload["embedded_package_paths"] = embedded_package_paths
        payload.update(outcome)
        print(json.dumps(payload, ensure_ascii=False))
        return EXIT_REFUSED if outcome["status"] == STATUS_REFUSED else 0

    payload, rewritten_manifest, changed = build_preparation_report(manifest_path, manifest_data)

    if not args.dry_run and changed:
        # The originals are recorded before the first real write: after it, the
        # pre-preparation content is gone and there is nothing left to save.
        backup_root, backup_failure = save_manifest_backup(
            manifest_path, project_path=project_path
        )
        payload["manifest_backup_path"] = str(backup_root)
        if backup_failure is not None:
            payload["status"] = STATUS_REFUSED
            payload["reason"] = backup_failure
            print(json.dumps(payload, ensure_ascii=False))
            return EXIT_REFUSED
        write_manifest(manifest_path, rewritten_manifest)
        # The hash describes what preparation just wrote, so a restore can tell an
        # untouched host from one somebody edited afterwards.
        hash_failure = record_written_manifest_hash(backup_root, manifest_path)
        if hash_failure is not None:
            payload["status"] = STATUS_REFUSED
            payload["reason"] = hash_failure
            print(json.dumps(payload, ensure_ascii=False))
            return EXIT_REFUSED

    payload["status"] = (
        STATUS_UNCHANGED if not changed else (STATUS_DRY_RUN if args.dry_run else STATUS_UPDATED)
    )
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
