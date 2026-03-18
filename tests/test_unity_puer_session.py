import sys
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
CLI_DIR = REPO_ROOT / "cli" / "python"
if str(CLI_DIR) not in sys.path:
    sys.path.insert(0, str(CLI_DIR))

import unity_puer_session  # type: ignore


class UnityPuerSessionAliasTests(unittest.TestCase):
    def test_legacy_alias_remains_a_thin_wrapper(self):
        with mock.patch.object(unity_puer_session.unity_puer_exec, "run_cli", return_value=(0, "", "")) as run_cli:
            exit_code, stdout, stderr = unity_puer_session.run_cli(
                [
                    "ensure-ready",
                    "--project-path",
                    "X:/project",
                    "--ready-timeout-seconds",
                    "5",
                ]
            )

        self.assertEqual((exit_code, stdout, stderr), (0, "", ""))
        self.assertEqual(
            run_cli.call_args.args[0],
            [
                "wait-until-ready",
                "--ready-timeout-seconds",
                "5.0",
                "--project-path",
                "X:/project",
                "--health-timeout-seconds",
                "2.0",
                "--activity-timeout-seconds",
                "20.0",
            ],
        )

    def test_legacy_alias_no_longer_accepts_unused_keep_unity_flag(self):
        with self.assertRaises(SystemExit) as ctx:
            unity_puer_session.run_cli(["ensure-ready", "--keep-unity"])

        self.assertEqual(ctx.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
