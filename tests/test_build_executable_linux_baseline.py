"""Linux AppImage CI stays on the Ubuntu 22.04 / glibc 2.35 baseline (#1818)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_linux_freeze_uses_ubuntu_22_04():
    workflow = (ROOT / ".github/workflows/build-executable.yml").read_text()
    assert "ubuntu-22.04" in workflow
    assert "- os: ubuntu-latest\n            platform: linux-x86_64" not in workflow
