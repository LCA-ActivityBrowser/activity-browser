"""Linux stand-alone CI must stay on an older glibc baseline (#1818)."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "build-executable.yml"


def test_linux_executable_job_uses_ubuntu_22_04():
    source = WORKFLOW.read_text(encoding="utf-8")
    assert "ubuntu-22.04" in source
    assert "platform: linux-x86_64" in source
    # Avoid regressing to ubuntu-latest for the Linux freeze matrix entry.
    assert "- os: ubuntu-latest\n            platform: linux-x86_64" not in source
    assert "check-appimage-glibc.sh" in source


def test_glibc_guard_script_exists():
    script = REPO_ROOT / "packaging" / "linux" / "check-appimage-glibc.sh"
    assert script.is_file()
    text = script.read_text(encoding="utf-8")
    assert "MAX_GLIBC" in text
    assert "2.35" in text
