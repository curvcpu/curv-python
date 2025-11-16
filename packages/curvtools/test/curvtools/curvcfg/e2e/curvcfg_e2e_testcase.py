import os
import shutil
import unittest
import subprocess
import sys
import pytest
from pathlib import Path

pytestmark = pytest.mark.e2e

class CurvCfgE2ETestCase(unittest.TestCase):
    pytestmark = pytest.mark.e2e
    @classmethod
    def make_curvcfg_base_cmd(cls) -> list[str]:
        """
        Prefer installed binary; fallback to module execution.
        """
        for name in ("curvcfg", "curv-cfg"):
            if shutil.which(name):
                return [name]
        return [sys.executable, "-m", "curvtools.cli.curvcfg"]

    @classmethod
    def setUpClass(cls) -> None:
        cls.base_cmd: list[str] = cls.make_curvcfg_base_cmd()

    def setUp(self) -> None:
        self._temp_paths: list[str] = []
        self._force_keep_temps: bool = False
        self._keep_paths: set[str] = set()
        self.addCleanup(self._cleanup_temp_paths)

    def register_temp_path(self, path: str) -> None:
        self._temp_paths.append(path)

    def _cleanup_temp_paths(self) -> None:
        # If the test failed or errored, keep temp paths for debugging
        if self._force_keep_temps:
            print(f"📣 keeping temp paths for debugging: {self._temp_paths}")
            return
        try:
            outcome = getattr(self, "_outcome", None)
            failed = False
            if outcome is not None:
                # Prefer result.failures/errors if available
                result = getattr(outcome, "result", None)
                if result is not None:
                    # Keep temps if this test failed OR if any test in the session failed
                    if result.failures or result.errors:
                        failed = True
                    pairs = list(result.failures) + list(result.errors)
                else:
                    pairs = list(getattr(outcome, "failures", [])) + list(getattr(outcome, "errors", []))
                for test, exc_info in pairs:
                    if test is self and exc_info is not None:
                        failed = True
                        break
            if failed or getattr(self, "_force_keep_temps", False):
                # Leave temp dirs/files in place
                print(f"📣 keeping temp paths for debugging: {self._temp_paths}")
                return
        except Exception:
            # On any introspection error, fall through to cleanup
            pass
        for p in getattr(self, "_temp_paths", []):
            try:
                if os.path.isdir(p):
                    if p in getattr(self, "_keep_paths", set()):
                        continue
                    shutil.rmtree(p, ignore_errors=True)
                elif os.path.isfile(p):
                    os.remove(p)
            except Exception:
                pass

    def tearDown(self) -> None:
        pass

    def run_cmd(self, cmd: list[str], cwd: str | None = None) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        try:
            repo_root = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip()
        except Exception:
            repo_root = os.getcwd()
        rel = env.get("CURV_FAKE_ROOT_REL", "packages/curvtools/test/curvtools/curvcfg/fake_curv_root")
        env["CURV_ROOT_DIR"] = os.path.join(repo_root, rel)
        # # Ensure workspace packages are importable in subprocesses
        # # Prepend so local sources take precedence over any installed versions
        # workspace_paths = [
        #     os.path.join(repo_root, "packages", "curvtools", "src"),
        #     os.path.join(repo_root, "packages", "curv", "src"),
        #     os.path.join(repo_root, "packages", "curvpyutils", "src"),
        # ]
        # existing_pythonpath = env.get("PYTHONPATH", "")
        # new_pythonpath = os.pathsep.join([p for p in workspace_paths if p] + ([existing_pythonpath] if existing_pythonpath else []))
        # env["PYTHONPATH"] = new_pythonpath
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env, cwd=cwd)
        if res.returncode != 0:
            # Mark to keep temps and print current temp paths for quick access
            self._force_keep_temps = True
            # Try to detect a --build-dir <path> in the invoked command and keep it explicitly
            if "--build-dir" in cmd:
                print(f"❤️ build-dir in cmd: {cmd}")
                idx = cmd.index("--build-dir")
                if idx + 1 < len(cmd):
                    bd = cmd[idx + 1]
                    if isinstance(bd, str):
                        self._keep_paths.add(bd)
            else:
                print(f"📣 build-dir not in cmd: {cmd}")
            print(f"📣 subprocess failed; keeping temp paths for debugging: {self._temp_paths}")
        return res
