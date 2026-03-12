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
        content = server_path.read_text(encoding="utf-8")

        self.assertIn("namespace UnityPuerExec", content)
        self.assertIn("CS.UnityPuerExec.UnityPuerExecBridge", content)
        self.assertNotIn("namespace C3.UnityPuerExecValidation", content)
        self.assertNotIn("CS.C3.UnityPuerExecValidation.UnityPuerExecBridge", content)


if __name__ == "__main__":
    unittest.main()
