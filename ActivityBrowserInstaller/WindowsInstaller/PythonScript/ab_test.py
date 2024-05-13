import os
import pytest
from ActivityBrowser import (
    getLatestRelease,
    getActivityBrowserVersion,
    isSecondIputVersionNewer,
)

@pytest.fixture
def create_dummy_exe(tmpdir):
    def _create(version):
        dummy_exe = tmpdir.join(f"ActivityBrowser-{version}")
        dummy_exe.write("test file")
        return dummy_exe
    return _create

def test_version_comparison(tmpdir, create_dummy_exe):
    # Step 1: Create a dummy EXE file with a version number of "1.0.0"
    dummy_exe_low = create_dummy_exe("1.0.0")

    # Obtain the version from the dummy EXE file
    current_version = getActivityBrowserVersion(tmpdir)

    # Latest release version
    latest_version = "3.1.2"

    # Check if the latest release version is newer than the current version
    assert isSecondIputVersionNewer(current_version, latest_version)

    # Remove the dummy EXE file
    os.remove(str(dummy_exe_low))

    # Step 2: Create a dummy EXE file with a version number of "4.0.0"
    dummy_exe_high = create_dummy_exe("4.0.0")

    # Obtain the version from the dummy EXE file
    current_version = getActivityBrowserVersion(tmpdir)

    os.remove(str(dummy_exe_high))

    # Check if the latest release version is newer than the current version
    assert not isSecondIputVersionNewer(current_version, latest_version)
