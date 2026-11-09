import ast
import inspect
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import tests.test_real_host_integration as real_host


REPO_ROOT = Path(__file__).resolve().parents[1]
# The real-host suite the window-read audit parses. Kept as a module constant so
# the guard and any future inspection read the same file.
REAL_HOST_SUITE_PATH = REPO_ROOT / "tests" / "test_real_host_integration.py"


def _device():
    class Device(real_host._SharedRealHostDevice, unittest.TestCase):
        def setUp(self):
            self.project_path = Path("host")

    device = Device()
    device.setUp()
    return device


def _request_id_segments_built_from_pid(source):
    """Return source segments that build a request id using os.getpid()."""
    tree = ast.parse(source)
    parents = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent
    flagged = []
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "getpid"
        ):
            continue
        # Climb to the enclosing expression/statement: the request id is
        # either assigned there or passed as a --request-id argument nearby.
        current = node
        while current is not None:
            segment = ast.get_source_segment(source, current) or ""
            if "request_id" in segment or "request-id" in segment:
                flagged.append(segment)
                break
            current = parents.get(current)
    return flagged


# ---------------------------------------------------------------------------
# Real-host window-read audit
#
# A real-host case that stages a dialog, runs a command and then inspects window
# state is only sound when the product does not act on the windows in between.
# Where the product auto-recovers a dialog (the ScriptUpdater consent prompt),
# a post-command scan is a race against the behavior it claims to measure. The
# audit below derives that inventory from the suite source instead of a
# hand-maintained list, so a new case is covered without a second place to
# update. See openspec/specs/validation-host-integration/spec.md.
# ---------------------------------------------------------------------------

# Calls that observe editor window state through the blocker API.
WINDOW_READ_CALLS = frozenset(
    {
        "_list_windows_dialogs",
        "detect_modal_blocker",
        "_is_modal_window",
        "_list_supported_windows_dialogs",
        "_list_supported_api_updater_dialogs",
    }
)
# CLI commands that observe window state. `get-blocker-state` is the same read
# through the product surface.
WINDOW_READ_COMMANDS = frozenset({"get-blocker-state"})
# CLI commands through which the product itself may act on windows.
PRODUCT_STAGE_COMMANDS = frozenset(
    {
        "exec",
        "wait-for-exec",
        "wait-for-compile",
        "stop",
        "ensure-closed",
        "pause-play-mode",
        "resume-play-mode",
        "enter-play-mode",
    }
)
# Helpers that themselves run a product-stage command or bring the host up.
PRODUCT_STAGE_HELPERS = frozenset(
    {
        "_warm_up_project_exec",
        "_exec_settled",
        "_start_shared_host",
        "_run_cli",
    }
)
# Textual markers of a dialog the product dismisses by itself. The ScriptUpdater
# fixture is the only such trigger in the suite.
AUTO_RECOVERED_DIALOG_TRIGGERS = (
    "_seed_obsolete_api_fixture",
    "ScriptUpdater",
    "api_updater_declined",
    "API_UPDATER_WARNING",
)


def _dotted_name(node):
    """Best-effort dotted name for a Call/Attribute/Name/Subscript chain."""
    parts = []
    while True:
        if isinstance(node, ast.Attribute):
            parts.append(node.attr)
            node = node.value
        elif isinstance(node, ast.Name):
            parts.append(node.id)
            return ".".join(reversed(parts))
        elif isinstance(node, ast.Call):
            node = node.func
        elif isinstance(node, ast.Subscript):
            node = node.value
        else:
            return ".".join(reversed(parts)) if parts else ""


def _literal_argv_head(call):
    """The command word of a `_run_cli([...])` list argument, if literal."""
    if not call.args:
        return None
    first = call.args[0]
    if not isinstance(first, (ast.List, ast.Tuple)) or not first.elts:
        return None
    head = first.elts[0]
    if isinstance(head, ast.Constant) and isinstance(head.value, str):
        return head.value
    return None


def _classify_suite_call(call):
    """Classify one call in the real-host suite as a window read or a staged command.

    The window-read class is decided **before** the generic staging branch: a
    ``get-blocker-state`` invocation also flows through ``_run_cli``, so a
    reversed order silently turns every window read into the command that
    preceded it. That bug shipped once in the spike and hid six cases.
    """
    leaf = _dotted_name(call.func).rsplit(".", 1)[-1]
    command = _literal_argv_head(call) if leaf == "_run_cli" else None
    if command in WINDOW_READ_COMMANDS:
        return "window_read", command
    if command in PRODUCT_STAGE_COMMANDS:
        return "product_stage", command
    if leaf in WINDOW_READ_CALLS:
        return "window_read", leaf
    if leaf in PRODUCT_STAGE_HELPERS:
        return "product_stage", leaf
    return None


def _window_reads_in_source_order(function_node, classify=None):
    """Every window read in one test function, each attributed to the command before it.

    Source order is enough: a real-host case is linear, so the last staged
    command seen before a read is the command that read follows. ``classify`` is
    injectable so a test can pin the branch order without patching the module.
    """
    if classify is None:
        classify = _classify_suite_call
    reads = []
    last_stage = None
    calls = sorted(
        (node for node in ast.walk(function_node) if isinstance(node, ast.Call)),
        key=lambda node: (node.lineno, node.col_offset),
    )
    for call in calls:
        classified = classify(call)
        if classified is None:
            continue
        kind, label = classified
        if kind == "product_stage":
            last_stage = {"label": label, "line": call.lineno}
            continue
        reads.append({"read": label, "read_line": call.lineno, "after": last_stage})
    return reads


def _references_auto_recovered_dialog(source, function_node):
    """Whether a case names a dialog the product dismisses by itself.

    Textual on purpose: a case can stage the consent dialog through a helper, and
    the trigger is the fixture or the product's own decline report. A miss fails
    open (the audit stays quiet) rather than failing a sound case.
    """
    segment = ast.get_source_segment(source, function_node) or ""
    return any(marker in segment for marker in AUTO_RECOVERED_DIALOG_TRIGGERS)


def _suite_window_read_inventory(source):
    """Per-case window-read inventory of the real-host suite source.

    Returns one record per ``test_*`` function that reads window state, in source
    order, with every read attributed to the staged command preceding it.
    """
    tree = ast.parse(source)
    inventory = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or not node.name.startswith("test_"):
            continue
        reads = _window_reads_in_source_order(node)
        if not reads:
            continue
        inventory.append(
            {
                "case": node.name,
                "line": node.lineno,
                "reads": reads,
                "auto_recovered_context": _references_auto_recovered_dialog(source, node),
            }
        )
    return sorted(inventory, key=lambda record: record["line"])


# Dialogs the suite stages that the product does *not* dismiss. A case staging one
# of these may read window state after a command: the read is the observation.
SOUND_STAGED_DIALOG_MARKERS = (
    ("_code_untitled_scene_save_dialog", "stages a save-scene prompt, which the product never dismisses"),
    (
        "_code_saved_scene_modified_prompt",
        "stages a modified-scene prompt, which the product never dismisses",
    ),
    (
        "EditorUtility.DisplayDialog",
        "stages an unknown prompt outside the catalog, which the product never dismisses",
    ),
    (
        "OpenProjectSettings",
        "stages non-blocking editor panels rather than a staging dialog",
    ),
    (
        "safe_mode_dialog",
        "observes a Safe Mode dialog the product leaves alone",
    ),
)

def _bound_names_from_reads(function_node):
    """Names bound to a window read, directly or transitively.

    Three shapes carry an observation forward:

    - direct: ``dialogs = _list_windows_dialogs(pid)``
    - derived helper: ``observed, others = _find_script_updater_dialog(dialogs)``
    - loop-selected: ``for d in dialogs: observed = d`` -- how a case picks one
      dialog out of the read, and how the race-shaped version expressed
      "the dialog this case needs".

    The loop form is what makes a restore-the-old-case check meaningful; without
    it the guard would miss exactly the shape it exists to forbid.
    """
    bound = {}
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        if not _mentions_window_read(node.value):
            continue
        target = node.targets[0]
        elements = target.elts if isinstance(target, (ast.Tuple, ast.List)) else [target]
        for element in elements:
            if isinstance(element, ast.Name):
                bound[element.id] = node.lineno

    # Fixpoint over two safe propagations only, so an unrelated assignment inside
    # a loop cannot be mistaken for an observation:
    #   - a loop target over a read-derived iterable (`for d in dialogs`)
    #   - an assignment whose value mentions a read-derived name (`observed = d`)
    changed = True
    while changed:
        changed = False
        for node in ast.walk(function_node):
            if isinstance(node, ast.For):
                iterated = {
                    child.id for child in ast.walk(node.iter) if isinstance(child, ast.Name)
                }
                if not (iterated & set(bound)):
                    continue
                target = node.target
                elements = (
                    target.elts if isinstance(target, (ast.Tuple, ast.List)) else [target]
                )
                for element in elements:
                    if isinstance(element, ast.Name) and element.id not in bound:
                        bound[element.id] = node.lineno
                        changed = True
                continue
            if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                continue
            assigned_names = {
                child.id for child in ast.walk(node.value) if isinstance(child, ast.Name)
            }
            if not (assigned_names & set(bound)):
                continue
            target = node.targets[0]
            # Tuple targets matter: `observed, others = _find_script_updater_dialog(dialogs)`
            # is how a case derives the dialog it then checks for presence.
            elements = (
                target.elts
                if isinstance(target, (ast.Tuple, ast.List))
                else [target]
            )
            for element in elements:
                if isinstance(element, ast.Name) and element.id not in bound:
                    bound[element.id] = node.lineno
                    changed = True
    return bound


def _mentions_window_read(node):
    """Whether an expression performs a window read.

    Derivation through a helper call is handled by the name fixpoint in
    ``_bound_names_from_reads``, not here: ``_find_script_updater_dialog(dialogs)``
    mentions the already-bound ``dialogs``, so it needs no special case.
    """
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            classified = _classify_suite_call(child)
            if classified is not None and classified[0] == "window_read":
                return True
    return False


def _decline_report_names(function_node):
    """Names bound to the product's own decline report (e.g. ``product_declined``)."""
    reported = set()
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        value_names = {
            child.id for child in ast.walk(node.value) if isinstance(child, ast.Name)
        } | {
            child.attr for child in ast.walk(node.value) if isinstance(child, ast.Attribute)
        }
        if any(marker in value_names for marker in ("warning", "API_UPDATER_WARNING")):
            target = node.targets[0]
            if isinstance(target, ast.Name):
                reported.add(target.id)
    return reported


def _presence_required_reads(function_node):
    """Control paths that require a window read to have found a dialog.

    The shape is ``if <read-derived name> is None: skip/fail`` -- the case cannot
    proceed unless the post-command read found the dialog, which is exactly the
    race this guard forbids. A test that also consults the product's decline
    report (``... and not product_declined``) is not presence-requiring: the
    product report carries the case and the read is a diagnostic.
    """
    bound = _bound_names_from_reads(function_node)
    decline_names = _decline_report_names(function_node)
    paths = []
    for node in ast.walk(function_node):
        if not isinstance(node, ast.If):
            continue
        checked = _none_checked_names(node.test)
        observed = sorted(checked & set(bound))
        if not observed:
            continue
        consulted = {
            child.id for child in ast.walk(node.test) if isinstance(child, ast.Name)
        } | {child.attr for child in ast.walk(node.test) if isinstance(child, ast.Attribute)}
        if consulted & decline_names or any(marker in consulted for marker in ("API_UPDATER_WARNING",)):
            continue
        if not _calls_skip_or_fail(node):
            continue
        for name in observed:
            paths.append({"name": name, "read_line": bound[name], "path_line": node.lineno})

    # A bare presence assertion is presence evidence too: `assertIsNotNone(obs)`
    # or `assertTrue(dialogs)` cannot pass unless the post-command read found the
    # dialog. An *absence* assertion (`assertIsNone(blocker)`) is the opposite and
    # is exactly what asserting the product's report looks like.
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr not in PRESENCE_ASSERTIONS:
            continue
        passed = {
            child.id for argument in node.args for child in ast.walk(argument)
            if isinstance(child, ast.Name)
        }
        for name in sorted(passed & set(bound)):
            paths.append({"name": name, "read_line": bound[name], "path_line": node.lineno})
    return paths


def _none_checked_names(test):
    """Names whose *absence* is tested (``x is None`` / ``x == None``).

    ``x is not None`` is the opposite polarity: it is the branch that runs when
    the dialog *was* found, so it is not evidence that the case requires one.
    """
    names = set()
    for node in ast.walk(test):
        if not isinstance(node, ast.Compare):
            continue
        operands = [node.left] + list(node.comparators)
        for operator, left, right in zip(node.ops, operands, operands[1:]):
            if not isinstance(operator, (ast.Is, ast.Eq)):
                continue
            is_none = any(
                isinstance(side, ast.Constant) and side.value is None for side in (left, right)
            )
            if not is_none:
                continue
            for side in (left, right):
                if isinstance(side, ast.Name):
                    names.add(side.id)
    return names


PRESENCE_ASSERTIONS = frozenset(
    {"assertIsNotNone", "assertTrue", "assertIn", "assertGreater", "assertIsInstance"}
)


def _calls_skip_or_fail(node):
    for child in ast.walk(node):
        if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
            if child.func.attr in ("skipTest", "fail"):
                return True
    return False


def _sound_read_reason(source, function_node, auto_recovered):
    """Why a post-command window read is sound rather than a race.

    The message contract: every post-command read is reported with its reason, so
    a reader sees an explained `sound` rather than an unexplained exception.
    """
    segment = ast.get_source_segment(source, function_node) or ""
    if auto_recovered:
        return (
            "asserts the product's own decline report; its window reads are "
            "diagnostics, not presence evidence"
        )
    for marker, reason in SOUND_STAGED_DIALOG_MARKERS:
        if marker in segment:
            return reason
    return "stages a dialog the product leaves alone"


def audit_window_reads(source):
    """The guard's finding over the real-host suite source.

    ``violations`` name the case, the read and the staged command preceding it.
    ``sound`` names the reason each other post-command read is legitimate, so an
    over-broad guard cannot pass by silently flagging nothing.
    """
    violations = []
    sound = []
    tree = ast.parse(source)
    functions = {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
    }
    for record in _suite_window_read_inventory(source):
        function_node = functions[record["case"]]
        post_command = [read for read in record["reads"] if read["after"] is not None]
        if not post_command:
            continue
        if not record["auto_recovered_context"]:
            sound.append(
                {
                    "case": record["case"],
                    "line": record["line"],
                    "reads": post_command,
                    "reason": _sound_read_reason(source, function_node, False),
                }
            )
            continue
        presence_paths = _presence_required_reads(function_node)
        if not presence_paths:
            sound.append(
                {
                    "case": record["case"],
                    "line": record["line"],
                    "reads": post_command,
                    "reason": _sound_read_reason(source, function_node, True),
                }
            )
            continue
        for path in presence_paths:
            # Name the read that actually produced the bound value, not just the
            # first window read in the case: a case may perform several.
            matching = [
                read for read in record["reads"] if read["read_line"] == path["read_line"]
            ]
            read_label = matching[0]["read"] if matching else post_command[0]["read"]
            violations.append(
                {
                    "case": record["case"],
                    "line": record["line"],
                    "read": read_label,
                    "read_line": path["read_line"],
                    "path_line": path["path_line"],
                    "stage": post_command[0]["after"]["label"],
                    "stage_line": post_command[0]["after"]["line"],
                }
            )
    return {"violations": violations, "sound": sound}


def format_window_read_audit(audit):
    """The guard's failure message: case names and lines, never a bare count."""
    lines = [
        "real-host cases assert an auto-recovered dialog from a post-command window read:"
    ]
    for violation in audit["violations"]:
        lines.append(
            "  - {} (line {}): {} after {} at line {} (presence required at line {})".format(
                violation["case"],
                violation["line"],
                violation["read"],
                violation["stage"],
                violation["stage_line"],
                violation["path_line"],
            )
        )
    return "\n".join(lines)


class RealHostReloadProbeTests(unittest.TestCase):
    def test_none_probe_then_ready_endpoint_returns_the_ready_payload(self):
        device = _device()
        ready = {"ok": True, "status": "ready", "refresh": {"pending": "not_pending"}}
        with mock.patch.object(
            real_host.unity_session, "_probe_health", return_value=(None, "dropped")
        ), mock.patch.object(
            real_host,
            "_scan_ready_control_endpoint",
            return_value=("http://127.0.0.1:55240", ready),
        ):
            base_url, payload = device._probe_through_reload_window(
                "http://127.0.0.1:55231", timeout_seconds=1
            )
        self.assertEqual(base_url, "http://127.0.0.1:55240")
        self.assertEqual(payload, ready)

    def test_health_fails_when_the_endpoint_never_returns(self):
        device = _device()
        with mock.patch.object(
            real_host.unity_session, "_probe_health", return_value=(None, "dropped")
        ), mock.patch.object(
            real_host, "_scan_ready_control_endpoint", return_value=(None, None)
        ), mock.patch.object(real_host.time, "sleep"):
            with self.assertRaises(AssertionError) as raised:
                device._health("http://127.0.0.1:55231", timeout_seconds=0)
        self.assertIn("reload window", str(raised.exception))

    def test_pending_wait_survives_a_dropped_endpoint_and_rebinds(self):
        device = _device()
        calls = {"n": 0}

        def scan(project_path, exclude_ports=(), timeout_seconds=1.5):
            calls["n"] += 1
            if calls["n"] < 2:
                return None, None
            return (
                "http://127.0.0.1:55240",
                {"ok": True, "status": "ready", "refresh": {"pending": "pending"}},
            )

        with mock.patch.object(
            real_host.unity_session, "_probe_health", return_value=(None, "WinError 10054")
        ), mock.patch.object(real_host, "_scan_ready_control_endpoint", side_effect=scan), mock.patch.object(
            real_host.time, "sleep"
        ):
            base_url, refresh = device._wait_for_refresh_pending(
                "http://127.0.0.1:55231", timeout_seconds=5
            )
        self.assertEqual(base_url, "http://127.0.0.1:55240")
        self.assertEqual(refresh["pending"], "pending")
        self.assertGreaterEqual(calls["n"], 2)

    def test_each_play_mode_helper_has_one_definition_on_the_shared_device(self):
        source = inspect.getsource(real_host)
        for name in (
            "_health",
            "_wait_for_refresh_pending",
            "_wait_for_refresh_state",
            "_wait_for_play_exit",
            "_exec_raw",
            "_exec_script",
            "_set_play_mode",
            "_write_compile_triggering_probe",
        ):
            self.assertEqual(source.count("def {}(".format(name)), 1, name)
            shared = getattr(real_host._SharedRealHostDevice, name)
            self.assertIs(getattr(real_host.RefreshOnChangeRealHostTests, name), shared, name)
            self.assertIs(getattr(real_host.PlayModeCompileBlockRealHostTests, name), shared, name)


class RealHostRequestIdUniquenessTests(unittest.TestCase):
    def test_helper_changes_value_on_each_call(self):
        first = real_host._unique_request_id("probe")
        second = real_host._unique_request_id("probe")
        self.assertTrue(first.startswith("probe-"))
        self.assertNotEqual(first, second)

    def test_no_exec_request_id_is_built_from_the_process_id_alone(self):
        flagged = _request_id_segments_built_from_pid(
            inspect.getsource(real_host)
        )
        self.assertEqual(
            flagged,
            [],
            "exec request ids must not be built from os.getpid(): {}".format(flagged),
        )


class RealHostResetTests(unittest.TestCase):
    def test_unknown_modal_is_cleared_before_the_next_case(self):
        device = _device()
        reads = {"n": 0}

        def run_cli(argv):
            if argv[0] == "get-blocker-state":
                reads["n"] += 1
                if reads["n"] == 1:
                    return (
                        0,
                        {
                            "result": {
                                "status": "modal_blocked",
                                "blocker": {
                                    "type": "unknown_modal_dialog",
                                    "hwnd": 42,
                                    "title": "Codex Validation Prompt",
                                    "buttons": [{"label": "OK"}, {"label": "Cancel"}],
                                },
                            }
                        },
                        "",
                        "",
                    )
                return 0, {"result": {"status": "clear"}}, "", ""
            self.assertEqual(argv[0], "resolve-blocker")
            self.assertIn("Cancel", argv)
            self.assertIn("42", argv)
            return 0, {"result": {"status": "resolved"}}, "", ""

        with mock.patch.object(real_host, "_run_cli", side_effect=run_cli), mock.patch.object(
            real_host.time, "sleep"
        ):
            device._clear_residual_modal_blocker()
        self.assertEqual(reads["n"], 2)

    def test_scene_restore_failure_names_the_step_that_broke(self):
        """A broken reset helper names its cause instead of an opaque payload.

        ``_restore_active_scene`` runs in setUp for every shared-device case, so a
        failure there fails the entire class identically. The JS side reports which
        step broke; the description must carry that through, otherwise 50-odd
        failures all read as "the suite is red" with no root cause.

        This is the regression pin for the PuerTS 2.2.2 defect: there,
        ``Assembly.GetType(string)`` could not be bound, so the type was never
        resolved and every case died here.
        """
        device = _device()
        payload = {"status": "completed", "result": {"path": "", "cleared": False,
                                                     "failure": "type_not_resolved",
                                                     "detail": "no loaded assembly exposes X"}}
        described = device._describe_restore_scene_failure(payload, payload["result"])
        self.assertIn("type_not_resolved", described)
        self.assertIn("no loaded assembly exposes X", described)

    def test_scene_restore_failure_distinguishes_dirty_from_uncleared(self):
        device = _device()
        dirty = device._describe_restore_scene_failure(
            {"status": "completed"},
            {"path": "Assets/__codex_host_reset/Baseline.unity", "dirty": True},
        )
        self.assertIn("still dirty", dirty)

        uncleared = device._describe_restore_scene_failure(
            {"status": "completed"},
            {"path": "Assets/__codex_host_reset/Baseline.unity", "dirty": False,
             "cleared": False},
        )
        self.assertIn("cleared: true", uncleared)

    def test_scene_restore_helper_does_not_use_unbindable_assembly_gettype(self):
        """Pin the binding: PuerTS 2.2.2 cannot bind Assembly.GetType(string).

        The helper must resolve the System.Type through GetTypes()+FullName, which
        binds on both PuerTS majors. A regression to ``.GetType('...')`` silently
        breaks every shared-device case on 2.2.2, so catch it statically here.
        """
        source = inspect.getsource(real_host._SharedRealHostDevice._restore_active_scene)
        self.assertNotIn(".GetType('", source)
        self.assertIn("GetTypes()", source)
        self.assertIn("candidate.FullName === target", source)

    def test_scene_restore_opens_the_baseline_scene(self):
        device = _device()
        seen = {}

        def exec_settled(base_url, code, wait_ms=None):
            seen["code"] = code
            return 0, {
                "result": {
                    "path": "Assets/__codex_host_reset/Baseline.unity",
                    "dirty": False,
                    "cleared": True,
                }
            }

        with mock.patch.object(device, "_ensure_shared_host_ready", return_value="http://127.0.0.1:55231"), \
                mock.patch.object(device, "_exec_settled", side_effect=exec_settled):
            device._restore_active_scene()
        self.assertIn("ClearSceneDirtiness", seen["code"])
        self.assertIn("SceneManager.GetActiveScene", seen["code"])
        self.assertNotIn("EditorSceneManager.GetActiveScene", seen["code"])
        self.assertIn("Assets/__codex_host_reset/Baseline.unity", seen["code"])
        self.assertNotIn("GetActiveScene().path", seen["code"])
        self.assertNotIn("SaveCurrentModifiedScenesIfUserWantsTo", seen["code"])

    def test_latched_temp_compile_error_retries_after_a_new_script(self):
        device = _device()
        calls = {"n": 0}

        def exec_settled(base_url, code, wait_ms=None):
            calls["n"] += 1
            if calls["n"] == 1:
                return 23, {
                    "status": "unity_compile_error",
                    "compile_messages": [
                        {
                            "message": "Assets/__codex_validation_temp/BrokenCompileErrorTest.cs(4,9): error CS0246",
                        }
                    ],
                }
            return 0, {
                "result": {
                    "path": "Assets/__codex_host_reset/Baseline.unity",
                    "dirty": False,
                    "cleared": True,
                }
            }

        with tempfile.TemporaryDirectory() as tmp:
            device.project_path = Path(tmp)
            broken = device.project_path / "Assets" / "__codex_validation_temp" / "BrokenCompileErrorTest.cs"
            broken.parent.mkdir(parents=True)
            broken.write_text("broken\n", encoding="utf-8")
            with mock.patch.object(device, "_ensure_shared_host_ready", return_value="http://127.0.0.1:55231"), \
                    mock.patch.object(device, "_exec_settled", side_effect=exec_settled):
                device._restore_active_scene()
            self.assertFalse(broken.exists())
            probe = device.project_path / "Assets" / "__codex_validation_temp" / real_host.COMPILE_RECOVERY_PROBE_NAME
            self.assertTrue(probe.exists())
        self.assertEqual(calls["n"], 2)

    def test_missing_exec_record_retries_after_the_endpoint_returns(self):
        device = _device()
        calls = {"n": 0}

        def exec_settled(base_url, code, wait_ms=None):
            calls["n"] += 1
            if calls["n"] == 1:
                return 1, {"status": "missing", "error": "no recoverable record exists for request_id"}
            return 0, {
                "result": {
                    "path": "Assets/__codex_host_reset/Baseline.unity",
                    "dirty": False,
                    "cleared": True,
                }
            }

        with mock.patch.object(device, "_ensure_shared_host_ready", return_value="http://127.0.0.1:55231"), \
                mock.patch.object(device, "_exec_settled", side_effect=exec_settled), \
                mock.patch.object(
                    device,
                    "_probe_through_reload_window",
                    return_value=("http://127.0.0.1:55240", {"status": "ready"}),
                ):
            device._restore_active_scene()
        self.assertEqual(calls["n"], 2)

    def test_change_signal_is_reset_before_scene_restore(self):
        source = inspect.getsource(real_host._SharedRealHostDevice._reset_shared_host_state)
        self.assertLess(
            source.index("_drop_unimported_compile_probes"),
            source.index("_ensure_shared_host_ready"),
        )
        self.assertLess(
            source.index("_reset_change_signal_state"),
            source.index("_restore_active_scene"),
        )

    def test_unimported_compile_probe_is_removed_before_the_signal_health_read(self):
        device = _device()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            device.project_path = root
            hidden = root / "Assets" / "__codex_validation_temp" / ".not_imported"
            hidden.mkdir(parents=True)
            hidden_cs = hidden / "BaselineWalkProbe.cs"
            hidden_cs.write_text("internal static class BaselineWalkProbe {}\n", encoding="utf-8")
            hidden_scene = hidden / "Probe.unity"
            hidden_scene.write_text("%YAML\n", encoding="utf-8")
            imported = root / "Assets" / "__codex_validation_temp" / "Keep.cs"
            imported.write_text("internal static class Keep {}\n", encoding="utf-8")
            outside = root / "Assets" / "Game" / ".hidden" / "Keep.cs"
            outside.parent.mkdir(parents=True)
            outside.write_text("internal static class Outside {}\n", encoding="utf-8")

            def ensure():
                if hidden_cs.exists():
                    raise AssertionError("health read before the unimported probe was removed")
                device._last_host_health = {
                    "refresh": {"pending": "not_pending", "suppressed": False}
                }
                return "http://127.0.0.1:55231"

            with mock.patch.object(device, "_ensure_shared_host_ready", side_effect=ensure), \
                    mock.patch.object(device, "_exec_settled") as exec_settled, \
                    mock.patch.object(device, "_touch_compile_probe") as touch:
                device._reset_change_signal_state()
            self.assertFalse(hidden_cs.exists())
            self.assertTrue(hidden_scene.exists())
            self.assertTrue(imported.exists())
            self.assertTrue(outside.exists())
            exec_settled.assert_not_called()
            touch.assert_not_called()

    def test_drop_latched_temp_scripts_uses_the_derived_extension_set(self):
        device = _device()
        with tempfile.TemporaryDirectory() as tmp:
            device.project_path = Path(tmp)
            root = Path(tmp) / "Assets" / "__codex_validation_temp"
            root.mkdir(parents=True)
            stubbed = root / "LatchedProbe.codexext"
            stubbed.write_text("stub\n", encoding="utf-8")
            ignored = root / "LatchedProbe.cs"
            ignored.write_text("stub\n", encoding="utf-8")
            with mock.patch.object(
                real_host,
                "_watched_compile_triggering_extensions",
                return_value=(".codexext",),
            ):
                device._drop_latched_temp_scripts()
            self.assertFalse(stubbed.exists())
            self.assertTrue(ignored.exists())

    def test_drop_unimported_compile_probes_uses_the_derived_extension_set(self):
        device = _device()
        with tempfile.TemporaryDirectory() as tmp:
            device.project_path = Path(tmp)
            hidden = Path(tmp) / "Assets" / "__codex_validation_temp" / ".not_imported"
            hidden.mkdir(parents=True)
            stubbed = hidden / "Probe.codexext"
            stubbed.write_text("stub\n", encoding="utf-8")
            ignored = hidden / "Probe.cs"
            ignored.write_text("stub\n", encoding="utf-8")
            with mock.patch.object(
                real_host,
                "_watched_compile_triggering_extensions",
                return_value=(".codexext",),
            ):
                device._drop_unimported_compile_probes()
            self.assertFalse(stubbed.exists())
            self.assertTrue(ignored.exists())

    def test_pending_signal_reset_writes_a_compilable_probe(self):
        device = _device()
        with tempfile.TemporaryDirectory() as tmp:
            device.project_path = Path(tmp)

            def ensure():
                device._last_host_health = {
                    "refresh": {"pending": "pending", "suppressed": False}
                }
                return "http://127.0.0.1:55231"

            with mock.patch.object(device, "_ensure_shared_host_ready", side_effect=ensure), \
                    mock.patch.object(
                        device,
                        "_exec_settled",
                        return_value=(0, {"result": {"pending": "NotPending"}}),
                    ), \
                    mock.patch.object(device, "_touch_compile_probe") as touch:
                device._reset_change_signal_state()
            touch.assert_called_once()

    def test_save_scene_cases_stage_their_own_scene(self):
        modified = inspect.getsource(real_host.RealHostIntegrationTests.test_resolve_blocker_cancel_is_rejected_for_save_scene_against_real_host)
        untitled = inspect.getsource(real_host.RealHostIntegrationTests.test_get_blocker_state_reports_save_scene_dialog_against_real_host)
        self.assertIn("_code_saved_scene_modified_prompt", modified)
        self.assertNotIn("GetActiveScene", modified)
        self.assertIn("_code_untitled_scene_save_dialog", untitled)
        self.assertIn("NewScene", inspect.getsource(real_host._SharedRealHostDevice._code_untitled_scene_save_dialog))
        self.assertIn("SaveScene", inspect.getsource(real_host._SharedRealHostDevice._code_saved_scene_modified_prompt))

    def test_script_updater_skip_path_uses_the_shared_removal(self):
        source = inspect.getsource(
            real_host.RealHostIntegrationTests.test_script_updater_consent_dialog_recovery_against_real_host
        )
        self.assertIn("_remove_script_updater_fixture", source)
        self.assertNotIn("fixture_path.unlink", source)
        device = _device()
        fixture = device.project_path / "Assets" / "__codex_validation_temp" / "ScriptUpdaterTriggerFixture.cs"
        with mock.patch.object(device, "_cleanup_temp_assets", return_value={"residue": []}) as cleanup, \
                mock.patch.object(real_host, "_scan_ready_control_endpoint", return_value=(None, None)):
            device._remove_script_updater_fixture(fixture)
        cleanup.assert_called_once_with(wait_for_editor=True)


class RealHostWindowReadAuditTests(unittest.TestCase):
    """Pins for the audit over the real-host suite source.

    Task 1.2: the *classifier* is pinned directly against synthetic snippets, not
    only through the whole-suite run. Without these, a renamed command or a
    reordered branch silently stops recognizing cases and the guard goes quiet.
    """

    def _inventory(self, source):
        return {record["case"]: record for record in _suite_window_read_inventory(source)}

    def test_get_blocker_state_is_a_window_read_and_not_the_stage_before_it(self):
        source = (
            "def test_case():\n"
            "    _run_cli([\"exec\", \"--code\", \"x\"])\n"
            "    _run_cli([\"get-blocker-state\", \"--project-path\", \"h\"])\n"
        )

        record = self._inventory(source)["test_case"]

        self.assertEqual([read["read"] for read in record["reads"]], ["get-blocker-state"])
        self.assertEqual(record["reads"][0]["after"]["label"], "exec")
        self.assertEqual(record["reads"][0]["after"]["line"], 2)

    def test_a_staging_helper_before_a_direct_list_is_ordered_correctly(self):
        source = (
            "def test_case():\n"
            "    _warm_up_project_exec(project, exe)\n"
            "    dialogs = unity_modal_blockers._list_windows_dialogs(pid)\n"
        )

        record = self._inventory(source)["test_case"]

        self.assertEqual(record["reads"][0]["read"], "_list_windows_dialogs")
        self.assertEqual(record["reads"][0]["after"]["label"], "_warm_up_project_exec")
        self.assertLess(record["reads"][0]["after"]["line"], record["reads"][0]["read_line"])

    def test_every_window_read_form_the_suite_uses_is_recognized(self):
        source = (
            "def test_case():\n"
            "    unity_modal_blockers._list_windows_dialogs(pid)\n"
            "    unity_modal_blockers.detect_modal_blocker(pid, scope='exec')\n"
            "    unity_modal_blockers._is_modal_window(hwnd)\n"
            "    unity_modal_blockers._list_supported_windows_dialogs(pid)\n"
            "    unity_modal_blockers._list_supported_api_updater_dialogs(pid)\n"
            "    _run_cli(['get-blocker-state', '--project-path', 'h'])\n"
        )

        record = self._inventory(source)["test_case"]

        self.assertEqual(
            [read["read"] for read in record["reads"]],
            [
                "_list_windows_dialogs",
                "detect_modal_blocker",
                "_is_modal_window",
                "_list_supported_windows_dialogs",
                "_list_supported_api_updater_dialogs",
                "get-blocker-state",
            ],
        )

    def test_a_case_without_a_window_read_is_absent_from_the_inventory(self):
        source = (
            "def test_case():\n"
            "    _run_cli(['exec', '--code', 'x'])\n"
            "    self.assertEqual(1, 1)\n"
        )

        self.assertEqual(self._inventory(source), {})

    def test_the_auto_recovered_dialog_marker_is_read_from_the_case_body_only(self):
        source = (
            "def test_with_trigger():\n"
            "    _seed_obsolete_api_fixture(project)\n"
            "    _run_cli(['exec', '--code', 'x'])\n"
            "    unity_modal_blockers._list_windows_dialogs(pid)\n"
            "\n"
            "def test_without_trigger():\n"
            "    _run_cli(['exec', '--code', 'x'])\n"
            "    unity_modal_blockers._list_windows_dialogs(pid)\n"
        )

        inventory = self._inventory(source)

        self.assertTrue(inventory["test_with_trigger"]["auto_recovered_context"])
        self.assertFalse(inventory["test_without_trigger"]["auto_recovered_context"])

    def test_reordering_the_window_read_branch_behind_the_staging_branch_loses_a_read(self):
        """The spike's own first-pass bug: a get-blocker-state read became a stage.

        Holds the classifier's branch order fixed by asserting the read-first
        result, and shows that the reversed order would report no read at all.
        """
        source = (
            "def test_case():\n"
            "    _run_cli(['get-blocker-state', '--project-path', 'h'])\n"
        )
        function_node = ast.parse(source).body[0]

        self.assertEqual(len(_window_reads_in_source_order(function_node)), 1)

        # The reversed order: match `_run_cli` as a staging helper before the argv
        # head is inspected, so the read is never reported. Six cases vanished
        # this way in the spike's first pass.
        def reversed_order(call):
            leaf = _dotted_name(call.func).rsplit(".", 1)[-1]
            if leaf in PRODUCT_STAGE_HELPERS:
                return "product_stage", leaf
            return _classify_suite_call(call)

        self.assertEqual(
            _window_reads_in_source_order(function_node, classify=reversed_order), []
        )


class RealHostWindowReadGuardTests(unittest.TestCase):
    """The guard over the suite's own source (tasks 2.1 and 2.2).

    A case that stages a dialog the product dismisses must assert the product's
    report, not the dialog's post-command presence. A case staging any other
    dialog may read window state after a command: the read *is* the observation.
    """

    def setUp(self):
        self.source = REAL_HOST_SUITE_PATH.read_text(encoding="utf-8")

    def test_a_race_shaped_case_fails_the_guard_by_name(self):
        race_shaped = (
            "def test_new_case():\n"
            "    fixture, original = _seed_obsolete_api_fixture(project)\n"
            "    _run_cli(['exec', '--code', 'x'])\n"
            "    dialogs = unity_modal_blockers._list_windows_dialogs(pid)\n"
            "    observed = None\n"
            "    for d in dialogs:\n"
            "        observed = d\n"
            "    if observed is None:\n"
            "        self.skipTest('could not be triggered')\n"
        )

        audit = audit_window_reads(race_shaped)

        self.assertEqual(
            [violation["case"] for violation in audit["violations"]], ["test_new_case"]
        )
        message = format_window_read_audit(audit)
        self.assertIn("test_new_case", message)
        self.assertIn("_list_windows_dialogs", message)
        self.assertIn("after exec", message)
        self.assertIn("line", message)

    def test_a_derived_helper_tuple_still_carries_the_observation(self):
        """Regression pin: the current case derives its dialog from a tuple assignment.

        `observed, others = _find_script_updater_dialog(dialogs)` must keep
        `observed` read-derived, or a presence check on it goes unseen. A fixpoint
        that only propagates through plain Name targets silently loses this.
        """
        source = (
            "def test_case():\n"
            "    _seed_obsolete_api_fixture(project)\n"
            "    _run_cli(['exec', '--code', 'x'])\n"
            "    dialogs = unity_modal_blockers._list_windows_dialogs(pid)\n"
            "    observed, others = _find_script_updater_dialog(dialogs)\n"
            "    if observed is None:\n"
            "        self.skipTest('could not be triggered')\n"
        )

        audit = audit_window_reads(source)

        self.assertEqual(["test_case"], [v["case"] for v in audit["violations"]])

    def test_a_bare_presence_assertion_on_the_read_is_also_a_violation(self):
        """The race can be expressed as an assertion, not only as a skip guard."""
        source = (
            "def test_case():\n"
            "    _seed_obsolete_api_fixture(project)\n"
            "    _run_cli(['exec', '--code', 'x'])\n"
            "    dialogs = unity_modal_blockers._list_windows_dialogs(pid)\n"
            "    self.assertTrue(dialogs)\n"
        )

        audit = audit_window_reads(source)

        self.assertEqual(["test_case"], [v["case"] for v in audit["violations"]])

    def test_an_absence_assertion_is_the_sound_shape(self):
        """``assertIsNone(blocker)`` says the product recovered the dialog."""
        source = (
            "def test_case():\n"
            "    _seed_obsolete_api_fixture(project)\n"
            "    _run_cli(['exec', '--code', 'x'])\n"
            "    blocker = unity_modal_blockers.detect_modal_blocker(pid, scope='exec')\n"
            "    self.assertIsNone(blocker)\n"
        )

        audit = audit_window_reads(source)

        self.assertEqual([], audit["violations"])

    def test_the_current_suite_has_no_violation(self):
        audit = audit_window_reads(self.source)

        self.assertEqual(
            [],
            audit["violations"],
            format_window_read_audit(audit),
        )

    def test_the_previous_race_shaped_version_of_the_case_is_named(self):
        """Task 2.1: restoring the old shape must fail the guard, by name.

        The pre-recovery version asserted the consent dialog's presence from a
        post-command scan, which is the exact shape the guard exists to forbid.
        """
        previous = (
            "def test_script_updater_consent_dialog_recovery_against_real_host():\n"
            "    fixture, original = _seed_obsolete_api_fixture(project)\n"
            "    _run_cli(['exec', '--code', 'x'])\n"
            "    dialogs = unity_modal_blockers._list_windows_dialogs(pid)\n"
            "    observed_api_dialog = None\n"
            "    for d in dialogs:\n"
            "        observed_api_dialog = d\n"
            "    if observed_api_dialog is None:\n"
            "        self.skipTest('ScriptUpdater consent dialog could not be triggered')\n"
        )

        audit = audit_window_reads(previous)

        self.assertEqual(
            [violation["case"] for violation in audit["violations"]],
            ["test_script_updater_consent_dialog_recovery_against_real_host"],
        )

    def test_the_six_sound_post_command_observations_are_not_flagged(self):
        """Task 2.2: the allowlist is pinned so an over-broad guard cannot pass."""
        audit = audit_window_reads(self.source)
        sound_cases = {record["case"] for record in audit["sound"]}

        expected = {
            "test_get_blocker_state_reports_save_scene_dialog_against_real_host",
            "test_resolve_blocker_cancels_modified_scene_prompt_against_real_host",
            "test_resolve_blocker_cancels_save_scene_dialog_against_real_host",
            "test_resolve_blocker_cancel_is_rejected_for_save_scene_against_real_host",
            "test_unknown_modal_dialog_is_reported_against_real_host",
            "test_non_blocking_editor_windows_are_not_blockers_against_real_host",
        }

        self.assertEqual(expected - sound_cases, set())

    def test_every_sound_observation_carries_its_reason(self):
        audit = audit_window_reads(self.source)

        self.assertTrue(audit["sound"], "the allowlist must not be empty")
        for record in audit["sound"]:
            self.assertTrue(record["reason"], record["case"])
        # No sound case falls through to the unexplained default.
        unexplained = [
            record["case"]
            for record in audit["sound"]
            if record["reason"] == "stages a dialog the product leaves alone"
        ]
        self.assertEqual([], unexplained)

    def test_a_save_scene_observation_is_reported_as_sound_with_its_reason(self):
        audit = audit_window_reads(self.source)
        reasons = {record["case"]: record["reason"] for record in audit["sound"]}

        reason = reasons["test_get_blocker_state_reports_save_scene_dialog_against_real_host"]
        self.assertIn("save-scene", reason)
        self.assertIn("never dismisses", reason)

    def test_a_case_that_requires_its_read_and_also_consults_the_decline_report_is_sound(self):
        """The distinction the guard encodes, in the direction that matters.

        Asserting the product's report is what carries the case; a window read next
        to it is a diagnostic, not the evidence. Without this, the guard could only
        be satisfied by deleting the reads entirely.
        """
        source = (
            "def test_case():\n"
            "    _seed_obsolete_api_fixture(project)\n"
            "    exit_code, payload, _, _ = _run_cli(['exec', '--code', 'x'])\n"
            "    dialogs = unity_modal_blockers._list_windows_dialogs(pid)\n"
            "    product_declined = payload.get('warning') == API_UPDATER_WARNING\n"
            "    if not dialogs and not product_declined:\n"
            "        self.skipTest('could not be triggered')\n"
        )

        audit = audit_window_reads(source)

        self.assertEqual([], audit["violations"])
        self.assertEqual(["test_case"], [record["case"] for record in audit["sound"]])
        self.assertIn("decline report", audit["sound"][0]["reason"])

    def test_every_post_command_read_is_either_a_violation_or_explained_sound(self):
        """The message contract: no post-command read is an unexplained exception."""
        audit = audit_window_reads(self.source)
        inventory = _suite_window_read_inventory(self.source)
        post_command_cases = {
            record["case"]
            for record in inventory
            if any(read["after"] for read in record["reads"])
        }
        accounted = {v["case"] for v in audit["violations"]} | {
            record["case"] for record in audit["sound"]
        }

        self.assertEqual(post_command_cases - accounted, set())


class ScriptUpdaterObservationClassificationTests(unittest.TestCase):
    """Task 3.1: an empty body from the consent dialog is not a mismatch.

    The case used to fail on an empty body with a fingerprint-extension message,
    which pointed at the wrong defect: the dialog had surfaced, the reader had
    simply returned nothing. These pins are pure Python and need no Editor.
    """

    MESSAGE = real_host.unity_modal_blockers.API_UPDATER_MESSAGE_FINGERPRINT

    def test_matching_body_is_a_match(self):
        observation = real_host._classify_script_updater_observation(
            {"title": "Script Updating Consent", "body": self.MESSAGE}
        )

        self.assertEqual(observation["outcome"], real_host.SCRIPT_UPDATER_OBSERVED_MATCHED)

    def test_empty_body_from_the_consent_title_is_an_unreadable_body(self):
        observation = real_host._classify_script_updater_observation(
            {
                "title": "Script Updating Consent",
                "body": "",
                "body_outcome": real_host.unity_modal_blockers.DIALOG_BODY_NO_READABLE_TEXT,
            }
        )

        self.assertEqual(
            observation["outcome"], real_host.SCRIPT_UPDATER_OBSERVED_UNREADABLE_BODY
        )
        self.assertTrue(observation["title_in_family"])
        self.assertEqual(
            observation["body_outcome"],
            real_host.unity_modal_blockers.DIALOG_BODY_NO_READABLE_TEXT,
        )

    def test_empty_body_defaults_to_the_absent_text_condition(self):
        # A dialog record from an older reader carries no body_outcome at all.
        observation = real_host._classify_script_updater_observation(
            {"title": "Script Updating Consent", "body": ""}
        )

        self.assertEqual(
            observation["body_outcome"],
            real_host.unity_modal_blockers.DIALOG_BODY_NO_READABLE_TEXT,
        )

    def test_enumeration_failure_is_kept_distinct_from_absent_text(self):
        observation = real_host._classify_script_updater_observation(
            {
                "title": "Script Updating Consent",
                "body": "",
                "body_outcome": real_host.unity_modal_blockers.DIALOG_BODY_ENUMERATION_FAILED,
            }
        )

        self.assertEqual(
            observation["outcome"], real_host.SCRIPT_UPDATER_OBSERVED_UNREADABLE_BODY
        )
        self.assertEqual(
            observation["body_outcome"],
            real_host.unity_modal_blockers.DIALOG_BODY_ENUMERATION_FAILED,
        )
        reason = real_host._unreadable_body_skip_reason(
            observation, {"title": "Script Updating Consent"}, "2022.3.62f2"
        )
        self.assertIn("window enumeration failed", reason)
        self.assertIn("2022.3.62f2", reason)
        self.assertIn("Script Updating Consent", reason)

    def test_absent_text_skip_reason_names_readability_not_triggering(self):
        observation = real_host._classify_script_updater_observation(
            {"title": "Script Updating Consent", "body": ""}
        )

        reason = real_host._unreadable_body_skip_reason(
            observation, {"title": "Script Updating Consent"}, "2022.3.62f2"
        )

        self.assertIn("carries no readable text", reason)
        self.assertIn("readability, not triggering", reason)
        self.assertNotIn("could not be triggered", reason)

    def test_non_empty_non_matching_body_is_still_a_fingerprint_miss(self):
        observation = real_host._classify_script_updater_observation(
            {"title": "Script Updating Consent", "body": "Some unrelated message"}
        )

        self.assertEqual(
            observation["outcome"], real_host.SCRIPT_UPDATER_OBSERVED_FINGERPRINT_MISS
        )
        self.assertEqual(observation["body"], "Some unrelated message")

    def test_title_family_covers_the_observed_editor_titles(self):
        for title in (
            "Script Updating Consent",
            "API Updating",
            "API Updater",
            "ScriptUpdater",
        ):
            self.assertTrue(real_host._is_script_updater_title(title), title)
        for title in ("Save Scene", "Enter Safe Mode?", "Unity"):
            self.assertFalse(real_host._is_script_updater_title(title), title)

    def test_unreadable_consent_dialog_is_still_found_by_its_title(self):
        # The message that would identify the dialog is exactly what could not
        # be read, so the title has to carry discovery on its own.
        candidate, others = real_host._find_script_updater_dialog(
            [
                {"hwnd": 2, "title": "Script Updating Consent", "body": ""},
                {"hwnd": 3, "title": "Save Scene", "body": ""},
            ]
        )

        self.assertEqual(candidate["hwnd"], 2)
        self.assertEqual([d["hwnd"] for d in others], [3])

    def test_unrelated_textless_dialog_is_not_the_consent_dialog(self):
        candidate, others = real_host._find_script_updater_dialog(
            [{"hwnd": 4, "title": "Delete Asset?", "body": ""}]
        )

        self.assertIsNone(candidate)
        self.assertEqual([d["hwnd"] for d in others], [4])

    def test_empty_body_on_an_unrelated_title_is_not_an_unreadable_consent_body(self):
        # Only the title family makes an empty body evidence about this case;
        # otherwise an unrelated textless dialog would be reported as the
        # ScriptUpdater's readability blocker.
        observation = real_host._classify_script_updater_observation(
            {"title": "Delete Asset?", "body": ""}
        )

        self.assertEqual(
            observation["outcome"], real_host.SCRIPT_UPDATER_OBSERVED_FINGERPRINT_MISS
        )
        self.assertFalse(observation.get("title_in_family", False))

    def test_fingerprint_matching_body_wins_over_the_title_family(self):
        # A dialog whose title is not in the family is still the consent dialog
        # when its body matches; the body is the real identifier.
        candidate, others = real_host._find_script_updater_dialog(
            [{"hwnd": 5, "title": "Unity", "body": self.MESSAGE}]
        )

        self.assertEqual(candidate["hwnd"], 5)
        self.assertEqual(others, [])


class RealHostCompileTriggeringProbeTests(unittest.TestCase):
    def test_watched_extensions_are_read_from_the_exec_help_statement(self):
        watched = real_host._watched_compile_triggering_extensions()
        self.assertEqual(watched, (".cs", ".asmdef", ".asmref", ".rsp"))

    def test_probe_without_a_watched_extension_is_rejected_before_writing(self):
        device = _device()
        with tempfile.TemporaryDirectory() as tmp:
            device.project_path = Path(tmp)
            with self.assertRaises(AssertionError) as raised:
                device._write_compile_triggering_probe("BaseUrlRefreshContinuationProbe")
            message = str(raised.exception)
            for extension in real_host._watched_compile_triggering_extensions():
                self.assertIn(extension, message)
            # Rejected before any validation-host write.
            self.assertEqual(list(Path(tmp).rglob("*")), [])

    def test_probe_with_a_watched_extension_still_stages(self):
        device = _device()
        with tempfile.TemporaryDirectory() as tmp:
            device.project_path = Path(tmp)
            probe = device._write_compile_triggering_probe("AutomaticRefreshProbe.cs")
            self.assertTrue(probe.exists())
            self.assertEqual(probe.suffix, ".cs")

    def test_pending_wait_failure_names_watched_extensions_and_skipped_reason(self):
        device = _device()
        health = {
            "ok": True,
            "status": "ready",
            "refresh": {"pending": "not_pending", "skipped_reason": "play_mode"},
        }
        with mock.patch.object(
            real_host.unity_session, "_probe_health", return_value=(None, "dropped")
        ), mock.patch.object(
            real_host, "_scan_ready_control_endpoint", return_value=("http://127.0.0.1:55240", health)
        ), mock.patch.object(real_host.time, "sleep"):
            with self.assertRaises(AssertionError) as raised:
                device._wait_for_refresh_pending("http://127.0.0.1:55231", timeout_seconds=0.3)
        message = str(raised.exception)
        self.assertIn("watched extensions", message)
        self.assertIn(".cs", message)
        self.assertIn("play_mode", message)

    def test_pending_wait_dropped_endpoint_keeps_its_own_message(self):
        device = _device()
        with mock.patch.object(
            real_host.unity_session, "_probe_health", return_value=(None, "dropped")
        ), mock.patch.object(
            real_host, "_scan_ready_control_endpoint", return_value=(None, None)
        ), mock.patch.object(real_host.time, "sleep"):
            with self.assertRaises(AssertionError) as raised:
                device._wait_for_refresh_pending("http://127.0.0.1:55231", timeout_seconds=0.3)
        message = str(raised.exception)
        self.assertIn("endpoint did not return", message)
        self.assertNotIn("change signal did not become pending", message)
