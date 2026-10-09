#!/usr/bin/python3
"""Robustheit: current_save/read_state/screenshot dürfen nicht abstürzen."""
import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tutor  # noqa: E402


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.game_data = self.root / "GameData"
        self.state = self.root / "state"
        self.state.mkdir()
        self._p1 = mock.patch.object(tutor, "GAME_DATA", self.game_data)
        self._p2 = mock.patch.object(tutor, "STATE", self.state)
        self._p1.start()
        self._p2.start()

    def tearDown(self):
        mock.patch.stopall()
        self.tmp.cleanup()

    def make_save(self, name, save_json=None, py=None, mtime=None):
        d = self.game_data / "Saves" / name
        d.mkdir(parents=True)
        if save_json is not None:
            (d / "save.json").write_text(save_json)
        for fname, content in (py or {}).items():
            (d / fname).write_text(content)
        if mtime is not None:
            os.utime(d / "save.json", (mtime, mtime))
        return d


class CurrentSave(Base):
    def test_missing_saves_dir(self):
        self.assertIsNone(tutor.current_save())

    def test_empty_saves_dir(self):
        (self.game_data / "Saves").mkdir(parents=True)
        self.assertIsNone(tutor.current_save())

    def test_save_dir_without_save_json(self):
        (self.game_data / "Saves" / "only_py").mkdir(parents=True)
        (self.game_data / "Saves" / "only_py" / "main.py").write_text("x = 1")
        self.assertIsNone(tutor.current_save())

    def test_picks_newest_by_mtime(self):
        self.make_save("old", save_json="{}", mtime=1000)
        self.make_save("new", save_json="{}", mtime=2000)
        self.assertEqual(tutor.current_save().name, "new")

    def test_saves_dir_is_a_file(self):
        self.game_data.mkdir(parents=True)
        (self.game_data / "Saves").write_text("not a dir")
        self.assertIsNone(tutor.current_save())


class ReadState(Base):
    def test_none_without_save(self):
        self.assertIsNone(tutor.read_state())

    def test_invalid_json_returns_none(self):
        self.make_save("broken", save_json="{ not json")
        self.assertIsNone(tutor.read_state())

    def test_missing_save_json_returns_none(self):
        self.make_save("nosave", py={"main.py": "pass"})
        self.assertIsNone(tutor.read_state())

    def test_unexpected_root_structure(self):
        self.make_save("listroot", save_json="[1, 2, 3]")
        st = tutor.read_state()
        self.assertIsNotNone(st)
        self.assertEqual(st["unlocks"], [])
        self.assertEqual(st["items"], {})

    def test_reads_code_unlocks_items(self):
        payload = json.dumps({
            "unlocks": ["move", "harvest"],
            "items": {"serializeList": [
                {"name": "wheat", "nr": 3},
                {"name": "carrot"},          # fehlendes "nr" wird übersprungen
            ]},
        })
        self.make_save("good", save_json=payload,
                       py={"main.py": "print(1)", "__builtins__.py": "SECRET"})
        st = tutor.read_state()
        self.assertEqual(st["save"], "good")
        self.assertEqual(st["code"], {"main.py": "print(1)"})  # builtins ausgeschlossen
        self.assertEqual(st["unlocks"], ["move", "harvest"])
        self.assertEqual(st["items"], {"wheat": 3})

    def test_unreadable_py_file_gives_partial(self):
        d = self.make_save("partial", save_json=json.dumps({"unlocks": []}),
                           py={"good.py": "a = 1"})
        bad = d / "bad.py"
        bad.write_text("b = 2")
        os.chmod(bad, 0)
        try:
            if os.access(str(bad), os.R_OK):
                self.skipTest("läuft als root – Berechtigungen greifen nicht")
            st = tutor.read_state()
            self.assertIsNotNone(st)
            self.assertEqual(st["code"], {"good.py": "a = 1"})
        finally:
            os.chmod(bad, stat.S_IRUSR | stat.S_IWUSR)


class Screenshot(Base):
    def test_swiftc_missing(self):
        with mock.patch.object(tutor.subprocess, "run", side_effect=FileNotFoundError("swiftc")):
            self.assertIsNone(tutor.screenshot())

    def test_helper_without_window_returns_none(self):
        helper = self.state / "winid"
        helper.write_text("#!/bin/sh\nexit 0\n")
        os.chmod(helper, 0o755)
        self.assertIsNone(tutor.screenshot())


if __name__ == "__main__":
    unittest.main()
