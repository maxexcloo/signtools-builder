"""Keep signing passwords out of GitHub error logs."""

import contextlib
import io
import os
import runpy
import subprocess
import tempfile
import traceback
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
PREPARE = runpy.run_path(ROOT / ".github/scripts/run_signer.py")["prepare_source"]
SAVE_SESSION = runpy.run_path(ROOT / ".github/scripts/save_session.py")["save_session"]
READER = """def read_file(file_path: StrPath):
    with open(file_path) as f:
        return f.read()
"""


class SignToolsBuilderTests(unittest.TestCase):
    def test_downloaded_credentials_are_masked_before_returning_to_signer(self):
        namespace = {"Path": Path, "StrPath": str}
        # Exercise the same patched upstream code that the wrapper executes.
        exec(compile(PREPARE(READER), "sign.py", "exec"), namespace)  # noqa: S102
        with tempfile.TemporaryDirectory() as directory:
            for name in (
                "account_2fa.txt",
                "account_name.txt",
                "account_pass.txt",
                "cert_pass.txt",
                "team_id.txt",
                "args.txt",
            ):
                with self.subTest(name=name):
                    path = Path(directory) / name
                    path.write_text("fixture%password\nsecond line")
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        result = namespace["read_file"](path)
                    self.assertEqual(result, "fixture%password\nsecond line")
                    expected = (
                        "::add-mask::fixture%25password%0Asecond line\n"
                        "::add-mask::fixture%25password\n"
                        "::add-mask::second line\n"
                        "::add-mask::fixture%25password\\nsecond line\n"
                        if name != "args.txt"
                        else ""
                    )
                    self.assertEqual(output.getvalue(), expected)

    def test_credential_masks_cover_subprocess_failure_representations(self):
        namespace = {"Path": Path, "StrPath": str}
        exec(compile(PREPARE(READER), "sign.py", "exec"), namespace)  # noqa: S102
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cert_pass.txt"
            for password in (
                "fixture'\"password",
                "fixture\\password",
                "fixtureépassword",
            ):
                with self.subTest(password=password):
                    path.write_text(password)
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        value = namespace["read_file"](path)
                    masks = [
                        line.removeprefix("::add-mask::")
                        for line in output.getvalue().splitlines()
                    ]
                    failures = (
                        subprocess.CalledProcessError(
                            1, ["security", "import", "fixture.p12", "-P", value]
                        ),
                        Exception(
                            f"Error logging in: {{'stderr': {value.encode()!r}}}"
                        ),
                    )
                    for failure in failures:
                        with self.subTest(failure=type(failure).__name__):
                            log = "".join(
                                traceback.format_exception(type(failure), failure, None)
                            )
                            for mask in sorted(masks, key=len, reverse=True):
                                log = log.replace(mask, "***")
                            self.assertIn("***", log)
                            self.assertNotIn(password, log)
                            self.assertNotIn(repr(password)[1:-1], log)
                            self.assertNotIn(repr(password.encode())[2:-1], log)

    def test_upstream_reader_changes_require_review(self):
        for source in ("def read_file(path): pass", READER + READER):
            with self.subTest(source=source), self.assertRaises(RuntimeError):
                PREPARE(source)


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
