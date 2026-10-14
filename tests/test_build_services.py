"""Unit tests for build-job preparation; no external build tools are executed."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.java_builder import prepare_java_build
from app.services.python_builder import prepare_python_build
from app.services.installer_builder import prepare_installer_build


class BuildServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        # Resolve Windows short-path aliases (for example RUNNER~1) consistently.
        self.root = Path(self.temp.name).resolve()
        self.tool = self.root / 'tool.exe'
        self.tool.write_bytes(b'MZ')

    def tearDown(self):
        self.temp.cleanup()

    def test_java_job_creates_launch4j_configuration(self):
        jar = self.root / 'App.jar'
        jar.write_bytes(b'jar')
        job = prepare_java_build(source=jar, output=self.root / 'out', name='Game',
                                 tool=self.tool)
        self.assertEqual(job['target'], self.root / 'out' / 'Game' / 'Game.exe')
        self.assertTrue((self.root / 'out' / 'Game' / 'launch4j.xml').is_file())
        self.assertEqual(job['args'][-1], str(self.root / 'out' / 'Game' / 'launch4j.xml'))

    def test_python_job_uses_onedir_and_hidden_imports(self):
        source = self.root / 'app.py'
        source.write_text('print(1)', encoding='utf-8')
        job = prepare_python_build(interpreter=sys.executable, source=source,
                                   output=self.root / 'out', name='Game',
                                   hidden='alpha, beta')
        self.assertIn('--onedir', job['args'])
        self.assertNotIn('--onefile', job['args'])
        self.assertIn('--hidden-import', job['args'])
        self.assertEqual(job['target'], self.root / 'out' / 'dist' / 'Game' / 'Game.exe')

    def test_python_builder_accepts_project_folder_and_excludes_dev_files(self):
        project = self.root / "AnimalDiceGame"
        (project / "animal_dice" / "assets" / "sounds").mkdir(parents=True)
        (project / ".venv" / "Lib").mkdir(parents=True)
        (project / ".idea").mkdir()
        (project / "tests").mkdir()
        (project / "main.py").write_text("print('game')", encoding="utf-8")
        (project / "animal_dice" / "assets" / "sounds" / "roll.wav").write_bytes(b"sound")
        (project / ".venv" / "Lib" / "bad.py").write_text("bad", encoding="utf-8")
        (project / ".idea" / "workspace.xml").write_text("ide", encoding="utf-8")
        (project / "tests" / "test_game.py").write_text("test", encoding="utf-8")

        job = prepare_python_build(interpreter=sys.executable, source=project,
                                   output=self.root / "out", name="AnimalDiceGame")
        self.assertEqual(job["source"], project / "main.py")
        self.assertEqual(job["cwd"], project)
        args = job["args"]
        self.assertIn("roll.wav", " ".join(args))
        self.assertNotIn("workspace.xml", " ".join(args))
        self.assertNotIn("bad.py", " ".join(args))
        self.assertNotIn("test_game.py", " ".join(args))

    def test_installer_job_creates_script_and_target(self):
        release = self.root / 'release'
        release.mkdir()
        (release / 'Game.exe').write_bytes(b'MZ')
        job = prepare_installer_build(compiler=self.tool, release_folder=release,
                                      exe_name='Game.exe', name='Game', version='1.0',
                                      publisher='Example', output=self.root / 'setup')
        self.assertTrue(job['script'].is_file())
        self.assertEqual(job['target'], self.root / 'setup' / 'Game_Setup.exe')

    def test_python_builder_selected_entry_file_collects_resources_and_skips_dev_folders(self):
        project = self.root / "Project"
        (project / "assets").mkdir(parents=True)
        (project / ".venv" / "Lib").mkdir(parents=True)
        (project / ".idea").mkdir()
        (project / "tests").mkdir()
        (project / "main.py").write_text("print('hello')", encoding="utf-8")
        (project / "assets" / "image.png").write_bytes(b"image")
        (project / ".venv" / "Lib" / "bad.dll").write_bytes(b"bad")
        (project / ".idea" / "workspace.xml").write_text("ide", encoding="utf-8")
        (project / "tests" / "test_x.py").write_text("test", encoding="utf-8")
        job = prepare_python_build(interpreter=sys.executable, source=project / "main.py",
                                  output=self.root / "out", name="Game")
        args = " ".join(job["args"])
        self.assertIn("image.png", args)
        self.assertNotIn("workspace.xml", args)
        self.assertNotIn("bad.dll", args)
        self.assertNotIn("test_x.py", args)

    def test_python_project_entrypoint_search_skips_output_folder(self):
        project = self.root / "Project"
        (project / "release").mkdir(parents=True)
        (project / "release" / "main.py").write_text("bad", encoding="utf-8")
        (project / "src").mkdir()
        (project / "src" / "main.py").write_text("good", encoding="utf-8")
        job = prepare_python_build(interpreter=sys.executable, source=project,
                                  output=project / "release", name="Game")
        self.assertEqual(job["source"], project / "src" / "main.py")


if __name__ == '__main__':
    unittest.main()
