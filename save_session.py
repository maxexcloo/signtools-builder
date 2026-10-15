"""Keep the authenticated Apple session in a repository secret, never in logs."""

import os
import subprocess
from pathlib import Path


def save_session(account_path=Path("account_name.txt")):
    if not account_path.is_file():
        print("No Apple account was downloaded; no session to save.")
        return
    account = account_path.read_text().strip()
    cookie_root = Path(os.environ.get("SPACESHIP_COOKIE_PATH", Path.home() / ".fastlane"))
    cookie = cookie_root / "spaceship" / account / "cookie"
    if not cookie.is_file() or not cookie.stat().st_size:
        print("No authenticated Apple session was created; saved session unchanged.")
        return
    result = subprocess.run(
        ["gh", "secret", "set", "FASTLANE_SESSION", "--repo", os.environ["GITHUB_REPOSITORY"]],
        capture_output=True,
        input=cookie.read_bytes(),
        timeout=30,
    )
    if result.returncode:
        raise RuntimeError("Could not save the Apple session to the repository secret")
    print("Apple session saved for subsequent signing jobs.")


if __name__ == "__main__":
    save_session()
