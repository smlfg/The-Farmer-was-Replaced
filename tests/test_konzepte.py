import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import konzepte as k  # noqa: E402


class KonzeptkarteTest(unittest.TestCase):
    def setUp(self):
        d = Path(tempfile.mkdtemp())
        self.patches = [mock.patch.object(k, "MAP", d / "konzepte.md"), mock.patch.object(k, "PRACTICE", d / "uebung.json")]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def test_only_known_ids_and_only_upward(self):
        k.save_map(k.load_map())
        self.assertEqual(k.apply_notes(["mit Hilfe: rueckgabewert – check gibt True zurück"]), [("rueckgabewert", "mit Hilfe")])
        self.assertEqual(k.apply_notes(["kann ich: Datei-Chaos beseitigt"]), [])        # kein Konzept der Liste
        self.assertEqual(k.apply_notes(["offen: rueckgabewert"]), [])                    # nie absteigen
        self.assertEqual(k.apply_notes(["selbstständig: rueckgabewert"]), [("rueckgabewert", "kann ich")])
        self.assertEqual(k.load_map()["rueckgabewert"]["stufe"], "kann ich")

    def test_learner_edit_wins(self):
        k.save_map(k.load_map())
        text = k.MAP.read_text().replace("| `liste` | Liste [] | offen |", "| `liste` | Liste [] | kann ich |")
        k.MAP.write_text(text)
        self.assertEqual(k.load_map()["liste"]["stufe"], "kann ich")
        self.assertEqual(k.apply_notes(["mit Hilfe: liste"]), [])                        # Coach überschreibt nicht nach unten
        self.assertIn("liste", k.summary().split("|")[0])                                # steht unter „kann ich“

    def test_detect_nested_loops_and_lists(self):
        code = {"a.py": "for i in range(3):\n\tfor j in range(3):\n\t\tmove(North)\n",
                "b.py": "x = []\nx.append((1, 2))\nprint(x[0])\n"}
        found = k.detect(code)
        self.assertIn("verschachtelte_schleifen", found)
        for cid in ("liste", "append", "tupel", "index", "print_debug"):
            self.assertIn(cid, found)
        self.assertNotIn("global", found)


class SerieTest(unittest.TestCase):
    def setUp(self):
        self.p = mock.patch.object(k, "PRACTICE", Path(tempfile.mkdtemp()) / "uebung.json")
        self.p.start()

    def tearDown(self):
        self.p.stop()

    def write(self, tage):
        k.PRACTICE.write_text(json.dumps({"tage": {d: {"minuten": m} for d, m in tage.items()}}))

    def test_consecutive_days(self):
        self.write({"2026-10-08": 30, "2026-10-09": 480, "2026-10-10": 26})
        self.assertEqual(k.streak(today="2026-10-10"), 3)

    def test_today_not_yet_reached_keeps_streak(self):
        self.write({"2026-10-09": 480, "2026-10-10": 5})
        self.assertEqual(k.streak(today="2026-10-10"), 1)

    def test_gap_breaks_streak(self):
        self.write({"2026-10-07": 60, "2026-10-09": 30})
        self.assertEqual(k.streak(today="2026-10-09"), 1)

    def test_minute_counted_once(self):
        self.assertTrue(k.record_activity("10:00"))
        self.assertFalse(k.record_activity("10:00"))
        self.assertTrue(k.record_activity("10:01"))
        self.assertEqual(k.today_minutes(), 2)


class LehrplanTest(unittest.TestCase):
    def test_lesson_for_day(self):
        self.assertEqual(k.lesson("2026-10-13")[0], "Rückgabewert (return ist nicht print)")
        self.assertIsNone(k.lesson("2026-12-24"))
        self.assertIn("Rückgabewert", k.lesson_intro("2026-10-13"))
        self.assertEqual(k.lesson_intro("2026-12-24"), "")
        self.assertNotIn("`", k.lesson_line("2026-10-10"))

    def test_plan_has_14_days(self):
        days = [k.lesson("2026-10-%02d" % d) for d in range(10, 24)]
        self.assertTrue(all(days))


if __name__ == "__main__":
    unittest.main()
