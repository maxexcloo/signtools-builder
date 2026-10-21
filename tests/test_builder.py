"""Keep signing passwords out of GitHub error logs."""

import contextlib
import io
import os
import runpy
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
SAVE_SESSION = runpy.run_path(ROOT / ".github/scripts/save_session.py")["save_session"]


class SigningWorkflowTests(unittest.TestCase):
    def test_signer_output_stays_private_on_success_and_failure(self):
        workflow = (ROOT / ".github/workflows/sign.yaml").read_text()
        step = workflow.split("        name: Sign App\n", 1)[1]
        run = step.split("        run: |\n", 1)[1]
        script = textwrap.dedent(run.split("        working-directory:", 1)[0])
        with tempfile.TemporaryDirectory() as directory:
            signer = Path(directory) / "sign.py"
            for returncode in (0, 1):
                with self.subTest(returncode=returncode):
                    signer.write_text(
                        "import sys\n"
                        "print('fixture-private-stdout')\n"
                        "print('fixture-private-stderr', file=sys.stderr)\n"
                        f"sys.exit({returncode})\n"
                    )
                    result = subprocess.run(
                        ["bash", "-c", script],
                        capture_output=True,
                        check=False,
                        cwd=directory,
                        text=True,
                    )
                    self.assertEqual(result.returncode, returncode)
                    self.assertEqual(result.stderr, "")
                    self.assertEqual(
                        result.stdout,
                        "Signing completed.\n"
                        if not returncode
                        else "::error::Signing failed; review the job in SignTools.\n",
                    )


class AppleSessionTests(unittest.TestCase):
    def test_only_the_selected_accounts_cookie_is_sent_via_stdin(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            account = root / "account_name.txt"
            account.write_text("fixture@example.invalid")
            cookie = root / "spaceship/fixture@example.invalid/cookie"
            cookie.parent.mkdir(parents=True)
            cookie.write_bytes(b"fixture-session-cookie")
            other = root / "spaceship/other@example.invalid/cookie"
            other.parent.mkdir(parents=True)
            other.write_bytes(b"other-session-cookie")
            environment = {
                "GITHUB_REPOSITORY": "fixture/builder",
                "SPACESHIP_COOKIE_PATH": directory,
            }
            for returncode in (0, 1):
                with (
                    self.subTest(returncode=returncode),
                    mock.patch.dict(os.environ, environment),
                    mock.patch("subprocess.run") as run,
                    contextlib.redirect_stdout(io.StringIO()) as output,
                ):
                    run.return_value.returncode = returncode
                    run.return_value.stderr = b"fixture-session-cookie"
                    if returncode:
                        with self.assertRaisesRegex(RuntimeError, "Could not save"):
                            SAVE_SESSION(account)
                    else:
                        SAVE_SESSION(account)
                    run.assert_called_once()
                    self.assertEqual(
                        run.call_args.args[0],
                        [
                            "gh",
                            "secret",
                            "set",
                            "FASTLANE_SESSION",
                            "--repo",
                            "fixture/builder",
                        ],
                    )
                    self.assertEqual(
                        run.call_args.kwargs["input"], b"fixture-session-cookie"
                    )
                    self.assertNotIn("fixture-session-cookie", output.getvalue())

    def test_missing_account_or_cookie_does_not_overwrite_the_saved_session(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            mock.patch("subprocess.run") as run,
        ):
            account = Path(directory) / "account_name.txt"
            with contextlib.redirect_stdout(io.StringIO()):
                SAVE_SESSION(account)
                account.write_text("fixture@example.invalid")
                with mock.patch.dict(os.environ, {"SPACESHIP_COOKIE_PATH": directory}):
                    SAVE_SESSION(account)
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
