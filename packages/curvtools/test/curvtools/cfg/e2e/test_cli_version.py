from curvcfg_e2e_testcase import CurvCfgE2ETestCase
import pytest

pytestmark = pytest.mark.e2e

class TestVersionCommand(CurvCfgE2ETestCase):
    def test_version_exit_code_zero(self) -> None:
        res = self.run_cmd(self.base_cmd + ["--version"])
        self.assertEqual(res.returncode, 0, f"non-zero exit: {res.returncode}\nstdout:\n{res.stdout}\nstderr:\n{res.stderr}")

    def test_version_contains_product_name_and_tagline(self) -> None:
        res = self.run_cmd(self.base_cmd + ["--version"])
        combined = (res.stdout + "\n" + res.stderr).lower()
        self.assertIn("curvcfg", combined)
        self.assertIn("build config tool", combined)

    def test_version_is_consistent_across_runs(self) -> None:
        first = self.run_cmd(self.base_cmd + ["--version"])
        second = self.run_cmd(self.base_cmd + ["--version"])
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual((first.stdout + first.stderr).strip(), (second.stdout + second.stderr).strip())


