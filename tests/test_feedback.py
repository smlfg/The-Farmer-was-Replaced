#!/usr/bin/python3
"""Tests für die Lernenden-Rückkopplung (antwort / unlocked / Lernstand)."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import os as _os, tempfile as _tf
_os.environ["TUTOR_STATE"] = _tf.mkdtemp()  # nie ins echte ~/.tfwr-tutor schreiben
import tutor


class FeedbackTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = Path(self.tmp.name)
        self._state = tutor.STATE
        tutor.STATE = self.state

    def tearDown(self):
        tutor.STATE = self._state
        self.tmp.cleanup()

    # 1) antwort schreibt nach STATE/answer_in.txt
    def test_answer_writes_file(self):
        tutor.cmd_answer("Weil die Drohne nach Norden fährt.")
        p = self.state / "answer_in.txt"
        self.assertTrue(p.exists())
        self.assertEqual(p.read_text().strip(), "Weil die Drohne nach Norden fährt.")
        self.assertEqual(tutor.answer_path(), p)

    def test_empty_answer_writes_nothing(self):
        tutor.cmd_answer("   ")
        self.assertFalse((self.state / "answer_in.txt").exists())

    # 2) unlocked hängt an STATE/manual_unlocks.txt an
    def test_unlock_appends(self):
        tutor.cmd_unlock("trees")
        tutor.cmd_unlock("carrots")
        self.assertEqual(tutor.manual_unlocks(), ["trees", "carrots"])
        self.assertEqual((self.state / "manual_unlocks.txt").read_text().split(), ["trees", "carrots"])

    def test_manual_unlocks_empty_without_file(self):
        self.assertEqual(tutor.manual_unlocks(), [])

    def test_observation_reports_manual_unlock_as_unverified(self):
        tutor.cmd_unlock("trees")
        st = dict(save="s1", code={"main.py": "move(North)"}, unlocks=["move"], items={"Hay": 3})
        text = tutor.observation("Test", st, None, None, True)
        self.assertIn("vom Lernenden gemeldet, nicht belegt: trees", text)


class ParseTest(unittest.TestCase):
    def test_parse_extracts_text_and_notes(self):
        answer = ("SPRECHEN:\nDie Drohne steht bei x gleich zwei.\n"
                  "LERNSTAND:\n- behandelt: Position nach Anweisung\n")
        text, notes = tutor.parse(answer)
        self.assertIn("Drohne", text)
        self.assertEqual(notes, ["behandelt: Position nach Anweisung"])

    def test_parse_skip(self):
        text, notes = tutor.parse("SKIP")
        self.assertIsNone(text)
        self.assertEqual(notes, [])


if __name__ == "__main__":
    unittest.main()
