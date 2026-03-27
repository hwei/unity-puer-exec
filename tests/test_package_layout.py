import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "packages" / "com.txcombo.unity-puer-exec"
RELEASE_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "release.yml"
UNITY_IMPORTED_PUBLISHABLE_ASSETS = ("Editor", "package.json", "LICENSE")


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
        self.assertNotIn('CLI~.meta', workflow)

    def test_editor_assembly_uses_formal_identity(self):
        asmdef_path = PACKAGE_ROOT / "Editor" / "UnityPuerExec.Editor.asmdef"
        self.assertTrue(asmdef_path.exists())

        asmdef = json.loads(asmdef_path.read_text(encoding="utf-8"))
        self.assertEqual(asmdef["name"], "UnityPuerExec.Editor")
        self.assertEqual(asmdef["rootNamespace"], "UnityPuerExec")

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

    def test_compile_trigger_compatibility_moves_to_dedicated_file(self):
        server_path = PACKAGE_ROOT / "Editor" / "UnityPuerExecServer.cs"
        bridge_path = PACKAGE_ROOT / "Editor" / "UnityPuerExecBridge.cs"
        compat_path = PACKAGE_ROOT / "Editor" / "UnityPuerExecCompileCompat.cs"
        server_content = server_path.read_text(encoding="utf-8")
        bridge_content = bridge_path.read_text(encoding="utf-8")
        compat_content = compat_path.read_text(encoding="utf-8")

        self.assertTrue(compat_path.exists())
        self.assertNotIn("private const string CompileTriggerDirectory", server_content)
        self.assertNotIn("TriggerValidationCompile", bridge_content)
        self.assertIn("internal static class UnityPuerExecCompileCompat", compat_content)
        self.assertIn("public static class UnityPuerExecCompileCompatBridge", compat_content)
        self.assertIn("TriggerValidationCompile", compat_content)

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


if __name__ == "__main__":
    unittest.main()
