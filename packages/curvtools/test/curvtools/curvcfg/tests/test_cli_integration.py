import pytest
import subprocess
from shutil import which

pytestmark = [pytest.mark.e2e]


def test_cli_on_path():
    assert which("curv-cfg") or which("curvcfg")


def test_help_exits_zero():
    exe = "curv-cfg" if which("curv-cfg") else "curvcfg"
    result = subprocess.run([exe, "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "usage" in result.stdout.lower() or "help" in result.stdout.lower()


def test_plus_one_flag():
    exe = "curv-cache-tool"
    if not which(exe):
        pytest.skip(f"{exe} not found in PATH")
    result = subprocess.run([exe, "--plus-one", "100"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "101" in result.stdout
