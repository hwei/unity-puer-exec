import json
import re
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "packages" / "com.txcombo.unity-puer-exec"
RELEASE_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "release.yml"
UNITY_IMPORTED_PUBLISHABLE_ASSETS = ("Editor", "package.json", "LICENSE", "README.md")
EDITMODE_TEST_ASMDEF_RELATIVE_PATH = "Tests/EditMode/UnityPuerExec.EditMode.Tests.asmdef"
EDITMODE_TEST_SOURCE_RELATIVE_PATH = "Tests/EditMode/UnityPuerExecRefreshBlockRetentionTests.cs"

CLI_DIR = REPO_ROOT / "cli" / "python"
if str(CLI_DIR) not in sys.path:
    sys.path.insert(0, str(CLI_DIR))

import direct_exec_client  # type: ignore


class PackageLayoutTests(unittest.TestCase):
    def test_package_home_exists_with_formal_identity(self):
        package_json_path = PACKAGE_ROOT / "package.json"
        self.assertTrue(package_json_path.exists())

        package_json = json.loads(package_json_path.read_text(encoding="utf-8"))
        self.assertEqual(package_json["name"], "com.txcombo.unity-puer-exec")
        self.assertEqual(package_json["displayName"], "Unity Puer Exec")

    def test_package_publish_metadata_and_license_exist(self):
        package_json_path = PACKAGE_ROOT / "package.json"
        license_path = PACKAGE_ROOT / "LICENSE"
        self.assertTrue(license_path.exists())

        package_json = json.loads(package_json_path.read_text(encoding="utf-8"))
        license_text = license_path.read_text(encoding="utf-8")

        self.assertEqual(package_json["license"], "MIT")
        self.assertEqual(package_json["repository"]["type"], "git")
        self.assertEqual(
            package_json["repository"]["url"],
            "https://github.com/hwei/unity-puer-exec.git",
        )
        self.assertEqual(package_json["author"]["name"], "Will Huang")
        self.assertEqual(
            package_json["dependencies"]["com.tencent.puerts.core"],
            "3.0.0",
        )
        self.assertIn("MIT License", license_text)
        self.assertIn("Will Huang", license_text)

    def test_published_package_includes_readme(self):
        readme_path = PACKAGE_ROOT / "README.md"
        self.assertTrue(readme_path.exists())

    def test_publishable_unity_assets_keep_committed_meta_files(self):
        for relative_path in UNITY_IMPORTED_PUBLISHABLE_ASSETS:
            asset_path = PACKAGE_ROOT / relative_path
            meta_path = asset_path.parent / "{}.meta".format(asset_path.name)
            self.assertTrue(asset_path.exists(), "{} should exist".format(relative_path))
            self.assertTrue(meta_path.exists(), "{} should exist".format(meta_path.relative_to(PACKAGE_ROOT)))

    def test_release_workflow_copies_required_root_meta_files(self):
        workflow = RELEASE_WORKFLOW_PATH.read_text(encoding="utf-8")

        self.assertIn('Copy-Item "packages/com.txcombo.unity-puer-exec/Editor.meta"', workflow)
        self.assertIn('Copy-Item "packages/com.txcombo.unity-puer-exec/package.json.meta"', workflow)
        self.assertIn('Copy-Item "packages/com.txcombo.unity-puer-exec/LICENSE.meta"', workflow)
        self.assertIn('Copy-Item "packages/com.txcombo.unity-puer-exec/README.md.meta"', workflow)
        self.assertNotIn('CLI~.meta', workflow)

    def test_release_workflow_is_parseable_yaml_with_a_runnable_stamp_step(self):
        """Substring checks pass on a workflow GitHub cannot parse.

        The stamp step's script is written inside a YAML block scalar, where a
        column-0 line silently ends the scalar; that produced a workflow that
        every substring assertion accepted and no runner could execute.
        """
        try:
            import yaml  # type: ignore
        except ImportError:
            self.skipTest("PyYAML not installed")

        workflow = yaml.safe_load(RELEASE_WORKFLOW_PATH.read_text(encoding="utf-8"))
        steps = workflow["jobs"]["publish"]["steps"]
        stamp = next(s for s in steps if s.get("name", "").startswith("Stamp"))

        self.assertIn("CLI_VERSION", stamp["run"])
        self.assertIn("_build_version.py", stamp["run"])
        # A line at column 0 would have truncated the scalar above this point.
        for line in stamp["run"].splitlines():
            self.assertFalse(line.startswith("CLI_VERSION"), "stamp body escaped the block scalar")

    def test_release_workflow_stamps_and_verifies_the_cli_version(self):
        workflow = RELEASE_WORKFLOW_PATH.read_text(encoding="utf-8")

        stamp_index = workflow.index('Set-Content -Path "cli/python/_build_version.py"')
        build_index = workflow.index("--onefile")
        verify_index = workflow.index('& "dist/unity-puer-exec.exe" --version')
        assemble_index = workflow.index("Assemble UPM package tree")

        self.assertIn("CLI_VERSION =", workflow)
        # Stamp before the build, verify the built artifact before it is published.
        self.assertLess(stamp_index, build_index)
        self.assertLess(build_index, verify_index)
        self.assertLess(verify_index, assemble_index)

    def test_package_editmode_test_assembly_is_editor_only_and_gated(self):
        # The fast Unity-side harness must never leak into a player build or the
        # published package. The Editor-only platform and the UNITY_INCLUDE_TESTS
        # define constraint are what compile the assembly only for a test run; the
        # test-framework references make it a test assembly rather than product code.
        # This guard needs no Unity, so a mis-scoped asmdef fails the default suite.
        asmdef_path = PACKAGE_ROOT / EDITMODE_TEST_ASMDEF_RELATIVE_PATH
        self.assertTrue(
            asmdef_path.exists(),
            "{} should exist".format(EDITMODE_TEST_ASMDEF_RELATIVE_PATH),
        )

        asmdef = json.loads(asmdef_path.read_text(encoding="utf-8"))
        self.assertEqual(asmdef["includePlatforms"], ["Editor"])
        self.assertEqual(asmdef["excludePlatforms"], [])
        self.assertIn("UNITY_INCLUDE_TESTS", asmdef["defineConstraints"])
        self.assertIn("UnityPuerExec.Editor", asmdef["references"])
        self.assertIn("UnityEngine.TestRunner", asmdef["references"])
        self.assertIn("UnityEditor.TestRunner", asmdef["references"])
        self.assertTrue(asmdef["overrideReferences"])
        self.assertIn("nunit.framework.dll", asmdef["precompiledReferences"])
        self.assertFalse(asmdef["autoReferenced"])

        # The release workflow assembles the package from an explicit allowlist, so the
        # Tests tree stays a source-repository development surface.
        release_workflow = RELEASE_WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertNotIn("packages/com.txcombo.unity-puer-exec/Tests", release_workflow)

    def test_package_editmode_test_tree_keeps_committed_meta_files(self):
        # Unity needs the folder, asmdef, and source .meta files to import the tree
        # with a stable identity; the repository commits them like every other asset.
        for relative_path in (
            "Tests",
            "Tests/EditMode",
            EDITMODE_TEST_ASMDEF_RELATIVE_PATH,
            EDITMODE_TEST_SOURCE_RELATIVE_PATH,
        ):
            asset_path = PACKAGE_ROOT / relative_path
            meta_path = asset_path.parent / "{}.meta".format(asset_path.name)
            self.assertTrue(asset_path.exists(), "{} should exist".format(relative_path))
            self.assertTrue(
                meta_path.exists(),
                "{} should exist".format(meta_path.relative_to(PACKAGE_ROOT)),
            )

    def test_editor_assembly_uses_formal_identity(self):
        asmdef_path = PACKAGE_ROOT / "Editor" / "UnityPuerExec.Editor.asmdef"
        self.assertTrue(asmdef_path.exists())

        asmdef = json.loads(asmdef_path.read_text(encoding="utf-8"))
        self.assertEqual(asmdef["name"], "UnityPuerExec.Editor")
        self.assertEqual(asmdef["rootNamespace"], "UnityPuerExec")

    def test_published_endpoint_fields_come_only_from_the_running_process(self):
        # Task 2.5: the whole point of the publication is that the Editor states
        # facts about itself. A field derived from a machine-wide process listing
        # would reintroduce exactly the defect this change removes -- the CLI's old
        # session.json filled unity_pid from tasklist order. Pin on source that the
        # Editor-side publisher takes its pid from its own process and never
        # enumerates the machine's process table.
        publication_path = PACKAGE_ROOT / "Editor" / "UnityPuerExecEndpointPublication.cs"
        content = publication_path.read_text(encoding="utf-8")

        self.assertIn("Process.GetCurrentProcess().Id", content)
        # No machine-wide process enumeration anywhere in the publisher. (The .NET
        # enumeration APIs; not the word "tasklist", which appears in a comment
        # describing the very defect this publisher avoids.)
        self.assertNotIn("Process.GetProcesses", content)
        self.assertNotIn("GetProcessesByName", content)

    def test_cli_session_state_decision_does_not_consult_a_machine_process_list(self):
        # Task 2.5 / 4.6, CLI side: the session-state decision is made from the
        # project's own lockfile and publication. list_unity_pids must not appear in
        # the module that decides state, so a project's identity can never be derived
        # from machine-wide tasklist ordering.
        endpoint_path = REPO_ROOT / "cli" / "python" / "unity_session_endpoint.py"
        content = endpoint_path.read_text(encoding="utf-8")

        self.assertNotIn("list_unity_pids", content)

    def test_migrated_server_namespace_drops_validation_identity(self):
        server_path = PACKAGE_ROOT / "Editor" / "UnityPuerExecServer.cs"
        protocol_path = PACKAGE_ROOT / "Editor" / "UnityPuerExecProtocol.cs"
        content = server_path.read_text(encoding="utf-8")
        protocol_content = protocol_path.read_text(encoding="utf-8")

        self.assertIn("namespace UnityPuerExec", content)
        self.assertIn("CS.UnityPuerExec.UnityPuerExecBridge", protocol_content)
        self.assertNotIn("namespace C3.UnityPuerExecValidation", content)
        self.assertNotIn("CS.C3.UnityPuerExecValidation.UnityPuerExecBridge", protocol_content)

    def test_server_file_drops_dead_transitional_helpers(self):
        server_path = PACKAGE_ROOT / "Editor" / "UnityPuerExecServer.cs"
        content = server_path.read_text(encoding="utf-8")

        self.assertNotIn("public static class UnityPuerExecBatch", content)
        self.assertNotIn("private static string BuildStringArrayJson", content)

    def test_compiling_health_response_exposes_unity_pid_when_known(self):
        protocol_path = PACKAGE_ROOT / "Editor" / "UnityPuerExecProtocol.cs"
        content = protocol_path.read_text(encoding="utf-8")

        self.assertIn("compilingPidJson", content)
        branch_start = content.index("isCompilingOrReloading")
        branch_end = content.index("IsNullOrEmpty(envInitError)")
        compiling_branch = content[branch_start:branch_end]
        self.assertIn("compilingPidJson", compiling_branch)

    def test_compile_trigger_compatibility_residue_is_removed(self):
        server_path = PACKAGE_ROOT / "Editor" / "UnityPuerExecServer.cs"
        bridge_path = PACKAGE_ROOT / "Editor" / "UnityPuerExecBridge.cs"
        compat_path = PACKAGE_ROOT / "Editor" / "UnityPuerExecCompileCompat.cs"
        compat_meta_path = PACKAGE_ROOT / "Editor" / "UnityPuerExecCompileCompat.cs.meta"
        server_content = server_path.read_text(encoding="utf-8")
        bridge_content = bridge_path.read_text(encoding="utf-8")

        self.assertFalse(compat_path.exists())
        self.assertFalse(compat_meta_path.exists())
        self.assertNotIn("private const string CompileTriggerDirectory", server_content)
        self.assertNotIn("TriggerValidationCompile", bridge_content)

    def test_editor_runtime_split_moves_job_protocol_and_bridge_out_of_server_file(self):
        server_path = PACKAGE_ROOT / "Editor" / "UnityPuerExecServer.cs"
        job_state_path = PACKAGE_ROOT / "Editor" / "UnityPuerExecJobState.cs"
        protocol_path = PACKAGE_ROOT / "Editor" / "UnityPuerExecProtocol.cs"
        bridge_path = PACKAGE_ROOT / "Editor" / "UnityPuerExecBridge.cs"
        server_content = server_path.read_text(encoding="utf-8")
        job_state_content = job_state_path.read_text(encoding="utf-8")
        protocol_content = protocol_path.read_text(encoding="utf-8")
        bridge_content = bridge_path.read_text(encoding="utf-8")

        self.assertTrue(job_state_path.exists())
        self.assertTrue(protocol_path.exists())
        self.assertTrue(bridge_path.exists())
        self.assertNotIn("internal sealed class UnityPuerExecJob", server_content)
        self.assertNotIn("internal readonly struct UnityPuerExecJobSnapshot", server_content)
        self.assertNotIn("public static class UnityPuerExecBridge", server_content)
        self.assertIn("internal sealed class UnityPuerExecJob", job_state_content)
        self.assertIn("internal static class UnityPuerExecProtocol", protocol_content)
        self.assertIn("public static class UnityPuerExecBridge", bridge_content)
        self.assertNotIn("UnityPuerExecCompileCompatBridge.TriggerValidationCompile", protocol_content)
        self.assertNotIn("public static void Log", bridge_content)
        self.assertNotIn("public static int Port", bridge_content)

    def test_exec_protocol_guards_module_entry_contract_and_shared_globals(self):
        protocol_path = PACKAGE_ROOT / "Editor" / "UnityPuerExecProtocol.cs"
        protocol_content = protocol_path.read_text(encoding="utf-8")

        self.assertIn("globalThis.__unityPuerExecGlobals", protocol_content)
        self.assertIn("const __args =", protocol_content)
        self.assertIn("args: __args", protocol_content)
        self.assertIn("import __entry from", protocol_content)
        self.assertIn("missing_default_export", protocol_content)
        self.assertIn("missing_import_base_url", protocol_content)
        self.assertIn("default_export_must_be_function", protocol_content)
        self.assertIn("async_result_not_supported", protocol_content)
        self.assertIn("result_not_json_serializable", protocol_content)
        self.assertIn("DetectsImport", protocol_content)
        self.assertIn("BuildEntrySpecifier", protocol_content)

    def test_exec_protocol_supports_import_detection_without_comment_only_false_positives(self):
        protocol_path = PACKAGE_ROOT / "Editor" / "UnityPuerExecProtocol.cs"
        protocol_content = protocol_path.read_text(encoding="utf-8")

        self.assertIn("ImportDeclarationPattern", protocol_content)
        self.assertIn("StringAndCommentPattern", protocol_content)
        self.assertIn("new string(' ', match.Value.Length)", protocol_content)

    def test_exec_protocol_supports_stale_module_policy_and_recovery_contract(self):
        protocol_path = PACKAGE_ROOT / "Editor" / "UnityPuerExecProtocol.cs"
        protocol_content = protocol_path.read_text(encoding="utf-8")
        server_content = (PACKAGE_ROOT / "Editor" / "UnityPuerExecServer.cs").read_text(encoding="utf-8")
        job_content = (PACKAGE_ROOT / "Editor" / "UnityPuerExecJobState.cs").read_text(encoding="utf-8")

        self.assertIn("stale_module_policy", protocol_content)
        self.assertIn("TryNormalizeStaleModulePolicy", protocol_content)
        self.assertIn("BuildModuleCacheStaleErrorJson", protocol_content)
        self.assertIn("affected_modules", protocol_content)
        self.assertIn("RecordLocalModuleRead", server_content)
        self.assertIn("LocalModuleFingerprints", server_content)
        self.assertIn("CheckModuleStaleness", server_content)
        self.assertNotIn("SourceFileTimestamps", server_content)
        self.assertIn("RecoveryPerformed", job_content)

    def test_exec_server_owns_single_recovery_point_and_admission_order(self):
        server_content = (PACKAGE_ROOT / "Editor" / "UnityPuerExecServer.cs").read_text(encoding="utf-8")

        self.assertIn("if (execJob.RecoveryPerformed)", server_content)
        self.assertIn("ResetJsEnv();", server_content)
        self.assertIn('return "module_cache_stale";', server_content)
        self.assertIn('return "busy";', server_content)
        self.assertIn('"request_id_conflict"', server_content)
        self.assertLess(server_content.index('return "busy";'), server_content.index("staleModules = CheckModuleStaleness();"))
        self.assertLess(server_content.index('"request_id_conflict"'), server_content.index("staleModules = CheckModuleStaleness();"))

    def test_completion_log_reports_bounded_metadata_not_result_content(self):
        server_path = PACKAGE_ROOT / "Editor" / "UnityPuerExecServer.cs"
        content = server_path.read_text(encoding="utf-8")

        match = re.search(
            r"internal static void CompleteJob\(.*?\n        \}\n",
            content,
            re.DOTALL,
        )
        self.assertIsNotNone(match, "CompleteJob method body should exist")
        method_body = match.group(0)

        # The completion lifecycle log must not echo the full serialized result
        # (or any preview of it) into Editor.log; only bounded metadata.
        self.assertNotIn("result={resultJson}", method_body)
        self.assertIn("result_bytes=", method_body)
        self.assertIn("Encoding.UTF8.GetByteCount(resultJson)", method_body)
        # The stored job result and HTTP response are unaffected by the log change.
        self.assertIn("job.Complete(resultJson);", method_body)

    def test_cli_control_port_range_covers_every_port_the_service_can_bind(self):
        # The CLI discovers a project's endpoint by range scan, so the range it walks
        # must cover the range the control service binds. An earlier CLI bound of
        # 55250-exclusive omitted 55250 -- the last port the service can bind -- which
        # made an Editor there undiscoverable. The two sides live in different
        # languages, so pin the equality against the package source rather than
        # trusting the mirrored constants to stay in step.
        server_content = (PACKAGE_ROOT / "Editor" / "UnityPuerExecServer.cs").read_text(encoding="utf-8")
        preferred_match = re.search(r"PreferredPort\s*=\s*(\d+)", server_content)
        attempts_match = re.search(r"MaxPortAttempts\s*=\s*(\d+)", server_content)
        self.assertIsNotNone(preferred_match, "PreferredPort should be declared in the server")
        self.assertIsNotNone(attempts_match, "MaxPortAttempts should be declared in the server")
        service_preferred = int(preferred_match.group(1))
        service_attempts = int(attempts_match.group(1))

        self.assertEqual(direct_exec_client.CONTROL_PORT_PREFERRED, service_preferred)
        self.assertEqual(direct_exec_client.CONTROL_PORT_COUNT, service_attempts)
        self.assertEqual(
            direct_exec_client.CONTROL_PORT_END,
            service_preferred + service_attempts,
        )
        candidates = direct_exec_client.control_port_candidates()
        self.assertEqual(len(candidates), service_attempts)
        # The last port the service can bind is the last port the CLI scans.
        self.assertEqual(candidates[0], service_preferred)
        self.assertEqual(candidates[-1], service_preferred + service_attempts - 1)

    def _method_body(self, content, signature):
        match = re.search(
            re.escape(signature) + r"\s*\n        \{.*?\n        \}",
            content,
            re.DOTALL,
        )
        self.assertIsNotNone(match, "{} should exist".format(signature))
        return match.group(0)

    def test_compile_generation_advances_only_when_a_compilation_completes(self):
        # The compile generation is the signal the observe-compile-across-domain-reload
        # spike chose over the reload epochs (session_marker, SettledImportUtcTicks):
        # only a completed compilation may advance it. If the increment migrated to
        # afterAssemblyReload it would become a reload epoch and settle a reload that
        # compiled nothing.
        server_content = (PACKAGE_ROOT / "Editor" / "UnityPuerExecServer.cs").read_text(encoding="utf-8")

        compilation_finished = self._method_body(
            server_content, "private static void OnCompilationFinished(object obj)"
        )
        self.assertIn("AdvanceCompileGeneration();", compilation_finished)

        after_reload = self._method_body(
            server_content, "private static void OnAfterAssemblyReload()"
        )
        self.assertNotIn("AdvanceCompileGeneration", after_reload)

    def test_compile_generation_is_loaded_from_session_state_each_domain(self):
        # A plain static would reset to zero across the forced synchronous recompile's
        # domain reload and defeat the signal, so the value must round-trip
        # SessionState: persisted on advance and reloaded in the static constructor,
        # which runs once per domain.
        server_content = (PACKAGE_ROOT / "Editor" / "UnityPuerExecServer.cs").read_text(encoding="utf-8")

        self.assertIn(
            'private const string CompileGenerationSessionStateKey = "UnityPuerExec.CompileGeneration";',
            server_content,
        )
        load_body = self._method_body(
            server_content, "private static int LoadCompileGeneration()"
        )
        self.assertIn("SessionState.GetString(CompileGenerationSessionStateKey", load_body)

        advance_body = self._method_body(
            server_content, "private static void AdvanceCompileGeneration()"
        )
        self.assertIn("SessionState.SetString(CompileGenerationSessionStateKey", advance_body)

        static_ctor = re.search(
            r"static UnityPuerExecServer\(\)\s*\n        \{.*?\n        \}",
            server_content,
            re.DOTALL,
        )
        self.assertIsNotNone(static_ctor, "the UnityPuerExecServer static constructor should exist")
        self.assertIn("compileGeneration = LoadCompileGeneration();", static_ctor.group(0))

    def test_ready_health_response_reports_compile_generation(self):
        protocol_content = (PACKAGE_ROOT / "Editor" / "UnityPuerExecProtocol.cs").read_text(encoding="utf-8")
        server_content = (PACKAGE_ROOT / "Editor" / "UnityPuerExecServer.cs").read_text(encoding="utf-8")

        self.assertIn("int compileGeneration = 0", protocol_content)
        self.assertIn('compileGenerationJson', protocol_content)
        self.assertIn('\\"compile_generation\\":', protocol_content)
        # The generation is on the ready response only: a compiling service cannot
        # answer it, and reporting a value there would read as a false negative.
        ready_start = protocol_content.index("IsNullOrEmpty(envInitError)")
        not_available = protocol_content.index('\\"status\\":\\"not_available\\"')
        ready_branch = protocol_content[ready_start:not_available]
        self.assertIn("compileGenerationJson", ready_branch)
        self.assertIn("compileGeneration: compileGeneration", server_content)


    def test_ready_health_response_reports_play_state(self):
        protocol_content = (PACKAGE_ROOT / "Editor" / "UnityPuerExecProtocol.cs").read_text(encoding="utf-8")
        server_content = (PACKAGE_ROOT / "Editor" / "UnityPuerExecServer.cs").read_text(encoding="utf-8")

        self.assertIn('string playState = "edit"', protocol_content)
        self.assertIn("playStateJson", protocol_content)
        self.assertIn('\\"play_state\\":', protocol_content)
        # The value is sampled on the main thread in OnEditorUpdate and passed to the
        # health builder; the listening thread must not read Editor APIs directly.
        self.assertIn("playState = DerivePlayState();", server_content)
        self.assertIn("playState: playState", server_content)

        derive_body = self._method_body(server_content, "private static string DerivePlayState()")
        for state in ("edit", "entering", "exiting", "paused", "playing"):
            self.assertIn('"{}"'.format(state), derive_body)

    def test_play_mode_endpoint_runs_on_the_main_thread(self):
        server_content = (PACKAGE_ROOT / "Editor" / "UnityPuerExecServer.cs").read_text(encoding="utf-8")
        protocol_content = (PACKAGE_ROOT / "Editor" / "UnityPuerExecProtocol.cs").read_text(encoding="utf-8")

        self.assertIn('path.Equals("/play-mode", StringComparison.OrdinalIgnoreCase)', server_content)
        self.assertIn("BuildPlayModeResponseJson", protocol_content)

        handler_body = self._method_body(
            server_content, "private static async Task HandlePlayModeAsync(HttpListenerContext context)"
        )
        # Every play-state mutation is dispatched through the main-thread action queue.
        self.assertIn("MainThreadActions.Enqueue", handler_body)
        self.assertIn("EditorApplication.isPlaying = true;", handler_body)
        self.assertIn("EditorApplication.isPlaying = false;", handler_body)
        self.assertIn("EditorApplication.isPaused = true;", handler_body)
        # Pause is rejected in edit mode with a machine-readable status.
        self.assertIn('rejectedStatus = "invalid_play_state";', handler_body)

    def test_run_in_background_uses_session_state_hook_not_player_settings(self):
        hook_path = PACKAGE_ROOT / "Editor" / "UnityPuerExecPlayMode.cs"
        self.assertTrue(hook_path.exists())
        hook_content = hook_path.read_text(encoding="utf-8")
        server_content = (PACKAGE_ROOT / "Editor" / "UnityPuerExecServer.cs").read_text(encoding="utf-8")

        self.assertIn("[InitializeOnLoad]", hook_content)
        self.assertIn("EditorApplication.playModeStateChanged += OnPlayModeStateChanged;", hook_content)
        self.assertIn("PlayModeStateChange.EnteredPlayMode", hook_content)
        self.assertIn("SessionState.GetBool(ForceRunInBackgroundKey", hook_content)
        self.assertIn("SessionState.EraseBool(ForceRunInBackgroundKey);", hook_content)
        self.assertIn("Application.runInBackground = true;", hook_content)
        # The override must never be persisted to Player Settings. The server reads
        # the project's setting for disclosure only; the hook never touches it.
        self.assertNotIn("PlayerSettings", hook_content)
        self.assertIn("projectRunInBackground = PlayerSettings.runInBackground;", server_content)
        self.assertNotIn("PlayerSettings.runInBackground =", server_content)
        self.assertIn("UnityPuerExecPlayMode.RequestRunInBackground();", server_content)


if __name__ == "__main__":
    unittest.main()
