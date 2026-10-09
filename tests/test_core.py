"""Tests für die Kernlogik von tutor.py – ohne Netzwerk, Spiel oder Sprachausgabe."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import os as _os, tempfile as _tf
_os.environ["TUTOR_STATE"] = _tf.mkdtemp()  # nie ins echte ~/.tfwr-tutor schreiben
import tutor  # noqa: E402


class ParseTest(unittest.TestCase):
    def test_skip_gibt_none_und_leere_notes(self):
        self.assertEqual(tutor.parse("SKIP"), (None, []))
        self.assertEqual(tutor.parse("   SKIP\nirgendwas"), (None, []))
        self.assertEqual(tutor.parse("skip klein"), (None, []))

    def test_leere_eingabe(self):
        self.assertEqual(tutor.parse(""), (None, []))
        self.assertEqual(tutor.parse(None), (None, []))

    def test_sprechen_und_lernstand_getrennt(self):
        answer = "SPRECHEN:\nHallo Welt.\nLERNSTAND:\n- behandelt: Schleifen"
        text, notes = tutor.parse(answer)
        self.assertEqual(text, "Hallo Welt.")
        self.assertEqual(notes, ["behandelt: Schleifen"])

    def test_markdown_und_emoji_entfernt(self):
        answer = "SPRECHEN:\n**Move** `North` 🙂\nLERNSTAND:\n- behandelt: Syntax"
        text, notes = tutor.parse(answer)
        self.assertNotIn("*", text)
        self.assertNotIn("`", text)
        self.assertNotIn("🙂", text)
        self.assertIn("Move", text)
        self.assertIn("North", text)
        self.assertEqual(notes, ["behandelt: Syntax"])

    def test_fehlender_lernstand_keine_notes(self):
        text, notes = tutor.parse("SPRECHEN:\nNur ein Satz ohne Lernstand.")
        self.assertEqual(text, "Nur ein Satz ohne Lernstand.")
        self.assertEqual(notes, [])

    def test_nur_emoji_ergibt_none(self):
        text, notes = tutor.parse("SPRECHEN:\n🙂\nLERNSTAND:\n- behandelt: x")
        self.assertIsNone(text)
        self.assertEqual(notes, ["behandelt: x"])


class SaveProgressTest(unittest.TestCase):
    def test_keine_duplikate(self):
        with tempfile.TemporaryDirectory() as d:
            progress = Path(d) / "progress.md"
            with mock.patch.object(tutor, "PROGRESS", progress):
                tutor.save_progress(["behandelt: A", "behandelt: A"])
                tutor.save_progress(["behandelt: A", "gezeigt: B"])
                text = progress.read_text()
            self.assertEqual(text.count("behandelt: A"), 1)
            self.assertEqual(text.count("gezeigt: B"), 1)


class DocsForTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        docs = Path(self._tmp.name)
        (docs / "unlocks").mkdir()
        (docs / "scripting").mkdir()
        (docs / "unlocks" / "move.md").write_text("MOVE DOC")
        (docs / "unlocks" / "expand_1.md").write_text("EXPAND DOC")
        (docs / "unlocks" / "harvest.md").write_text("HARVEST DOC")
        self.docs = docs

    def tearDown(self):
        self._tmp.cleanup()

    def test_move_liefert_expand_1(self):
        with mock.patch.object(tutor, "DOCS", self.docs):
            out = tutor.docs_for(["move"])
        self.assertIn("MOVE DOC", out)
        self.assertIn("EXPAND DOC", out)

    def test_ohne_move_kein_expand_1(self):
        with mock.patch.object(tutor, "DOCS", self.docs):
            out = tutor.docs_for(["harvest"])
        self.assertIn("HARVEST DOC", out)
        self.assertNotIn("EXPAND DOC", out)

    def test_unbekannter_name_liefert_nichts(self):
        with mock.patch.object(tutor, "DOCS", self.docs):
            out = tutor.docs_for(["voellig_unbekannt"])
        self.assertEqual(out, "")


class ObservationTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.docs = Path(self._tmp.name)
        (self.docs / "unlocks").mkdir()
        (self.docs / "scripting").mkdir()
        self.patcher = mock.patch.object(tutor, "DOCS", self.docs)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self._tmp.cleanup()

    def _st(self, code):
        return {"save": "save1", "code": code, "unlocks": [], "items": {"weizen": 3}}

    def test_kein_screenshot_wenn_png_none(self):
        out = tutor.observation("Test", self._st({"main.py": "move()"}), None, None, False)
        self.assertIn("kein Screenshot", out)
        self.assertNotIn("angehängt", out)

    def test_geaenderte_datei_markiert(self):
        prev = {"code": {"main.py": "alt()"}, "unlocks": []}
        out = tutor.observation("Test", self._st({"main.py": "move()"}), prev, None, False)
        self.assertIn("(geändert)", out)

    def test_unveraenderte_datei_nicht_markiert(self):
        prev = {"code": {"main.py": "move()"}, "unlocks": []}
        out = tutor.observation("Test", self._st({"main.py": "move()"}), prev, None, False)
        self.assertNotIn("(geändert)", out)

    def test_screenshot_angehaengt_wenn_png(self):
        out = tutor.observation("Test", self._st({"main.py": "move()"}), None, b"png", False)
        self.assertIn("angehängt", out)


class ShouldSpeakTest(unittest.TestCase):
    def test_nicht_veraltet_wird_gesprochen_und_zahler_zuruckgesetzt(self):
        self.assertEqual(tutor.should_speak(False, 0), (True, 0))
        self.assertEqual(tutor.should_speak(False, 1), (True, 0))

    def test_erste_veraltete_antwort_verworfen(self):
        self.assertEqual(tutor.should_speak(True, 0), (False, 1))

    def test_zweite_veraltete_antwort_trotzdem_gesprochen(self):
        self.assertEqual(tutor.should_speak(True, 1), (True, 0))


class GamePidTest(unittest.TestCase):
    def _fake_run(self, pgrep_out, ps_map):
        def run(cmd, *args, **kwargs):
            stdout = pgrep_out if cmd[0] == "pgrep" else ps_map.get(cmd[-1], "")
            return type("R", (), {"stdout": stdout, "returncode": 0})()
        return run

    def test_ohne_pid_none(self):
        with mock.patch.object(tutor, "subprocess") as sub:
            sub.run = self._fake_run("", {})
            self.assertIsNone(tutor.game_pid())

    def test_ignoriert_fremde_prozesse(self):
        ps = {
            "111": "/Applications/Steam.app/Contents/MacOS/steam_osx",
            "333": "/System/Library/CoreServices/Overlay",
        }
        with mock.patch.object(tutor, "subprocess") as sub:
            sub.run = self._fake_run("111 333", ps)
            self.assertIsNone(tutor.game_pid())

    def test_erkennt_echtes_binary(self):
        ps = {
            "111": "/Applications/Steam.app/Contents/MacOS/steam_osx",
            "222": "/Applications/TheFarmerWasReplaced.app/Contents/MacOS/TheFarmerWasReplaced",
            "333": "/System/Library/CoreServices/Overlay",
        }
        with mock.patch.object(tutor, "subprocess") as sub:
            sub.run = self._fake_run("111 222 333", ps)
            self.assertEqual(tutor.game_pid(), 222)


if __name__ == "__main__":
    unittest.main()


class CadenceTest(unittest.TestCase):
    def test_stale_answer_spoken_after_long_silence(self):
        self.assertEqual(tutor.should_speak(True, 0, silent_for=75), (True, 0))
        self.assertEqual(tutor.should_speak(True, 0, silent_for=10), (False, 1))
