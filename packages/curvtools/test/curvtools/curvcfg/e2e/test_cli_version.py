import pytest
import subprocess

pytestmark = [pytest.mark.e2e]

class TestVersionCommand():
    def test_version_exit_code_zero(self) -> None:
        res = subprocess.run(
            [
                "curvcfg", 
                "--version"
            ], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True)
        assert res.returncode == 0, f"non-zero exit: {res.returncode}\nstdout:\n{res.stdout}\nstderr:\n{res.stderr}"

    def test_version_contains_product_name_and_tagline(self) -> None:
        res = subprocess.run(
            [
                "curvcfg", 
                "--version"
            ], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True)
        combined = (res.stdout + "\n" + res.stderr).lower()
        assert "curvcfg" in combined
        assert "build config tool" in combined

    def test_version_is_consistent_across_runs(self) -> None:
        first = subprocess.run(
            [
                "curvcfg", 
                "--version"
            ], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True)
        second = subprocess.run(
            [
                "curvcfg", 
                "--version"
            ], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True)
        assert first.returncode == 0, f"non-zero exit: {first.returncode}\nstdout:\n{first.stdout}\nstderr:\n{first.stderr}"
        assert second.returncode == 0, f"non-zero exit: {second.returncode}\nstdout:\n{second.stdout}\nstderr:\n{second.stderr}"
        assert (first.stdout + first.stderr).strip() == (second.stdout + second.stderr).strip()


