import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BAT = ROOT / "Start Career Discovery.bat"
COMMAND = ROOT / "Start Career Discovery.command"
SH = ROOT / "start.sh"
CHECK = ROOT / "scripts" / "starter-check.sh"
POSIX = (COMMAND, SH)


def dry_run(script, **extra):
    env = {k: v for k, v in os.environ.items() if not k.startswith("CD_")}
    env.update({"CD_DRY_RUN": "1", **extra})
    return subprocess.run(
        ["sh", str(script)], cwd="/", env=env, capture_output=True, text=True, timeout=30
    )


class StarterFiles(unittest.TestCase):
    def test_files_exist(self):
        for path in (BAT, COMMAND, SH, CHECK):
            self.assertTrue(path.is_file(), path.name)

    def test_line_endings(self):
        bat = BAT.read_bytes()
        self.assertIn(b"\r\n", bat)
        self.assertNotIn(b"\n", bat.replace(b"\r\n", b""))
        for path in (*POSIX, CHECK):
            self.assertNotIn(b"\r", path.read_bytes(), path.name)

    @unittest.skipIf(sys.platform == "win32", "POSIX permissions")
    def test_executable_bits(self):
        for path in (*POSIX, CHECK):
            self.assertTrue(os.access(path, os.X_OK), path.name)

    def test_contents(self):
        for path in (BAT, COMMAND, SH):
            text = path.read_text()
            self.assertIn("-m career_discovery app", text, path.name)
            self.assertIn("--no-project --python 3.12", text, path.name)
            self.assertIn("astral.sh", text, path.name)
            self.assertIn("Press Enter to continue or close this window to cancel", text, path.name)

    @unittest.skipIf(sys.platform == "win32", "needs sh")
    def test_syntax(self):
        for path in (COMMAND, SH, CHECK):
            self.assertEqual(subprocess.run(["sh", "-n", str(path)]).returncode, 0, path.name)
        if shutil.which("bash"):
            for path in (COMMAND, SH, CHECK):
                self.assertEqual(subprocess.run(["bash", "-n", str(path)]).returncode, 0, path.name)


@unittest.skipIf(sys.platform == "win32", "needs sh")
class StarterDryRun(unittest.TestCase):
    def test_uses_python_when_found(self):
        if not any(shutil.which(n) for n in ("python3", "python")):
            self.skipTest("no python on PATH")
        for path in POSIX:
            result = dry_run(path)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("-B -m career_discovery app", result.stdout)
            self.assertNotIn("uv run", result.stdout)

    def test_falls_back_to_uv(self):
        for path in POSIX:
            result = dry_run(path, CD_TEST_NO_PYTHON="1", CD_TEST_UV="/fake/uv")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("/fake/uv run --no-project --python 3.12 -- python -B -m career_discovery app", result.stdout)

    def test_offers_install_when_nothing_found(self):
        for path in POSIX:
            result = dry_run(path, CD_TEST_NO_PYTHON="1", CD_TEST_NO_UV="1")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("astral.sh", result.stdout)
            self.assertIn("Press Enter to continue or close this window to cancel", result.stdout)
            self.assertIn("install.sh", result.stdout)

    def test_path_with_spaces(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "Career Discovery Prototype"
            folder.mkdir()
            target = folder / SH.name
            shutil.copy(SH, target)
            result = dry_run(target, CD_TEST_NO_PYTHON="1", CD_TEST_UV="/fake/uv")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(str(folder), result.stdout)

    def test_check_script_passes(self):
        result = subprocess.run(["sh", str(CHECK)], capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
