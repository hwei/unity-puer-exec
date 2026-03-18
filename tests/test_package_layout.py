import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "packages" / "com.txcombo.unity-puer-exec"


class PackageLayoutTests(unittest.TestCase):
    def test_package_home_exists_with_formal_identity(self):
        package_json_path = PACKAGE_ROOT / "package.json"
        self.assertTrue(package_json_path.exists())

        package_json = json.loads(package_json_path.read_text(encoding="utf-8"))
        self.assertEqual(package_json["name"], "com.txcombo.unity-puer-exec")
        self.assertEqual(package_json["displayName"], "Unity Puer Exec")

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
        self.assertIn("UnityPuerExecCompileCompatBridge.TriggerValidationCompile", protocol_content)


if __name__ == "__main__":
    unittest.main()
