import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["TUTOR_STATE"] = tempfile.mkdtemp()  # nie ins echte ~/.tfwr-tutor schreiben
import tutor  # noqa: E402


class ParsePartsTest(unittest.TestCase):
    def setUp(self):
        self.p = mock.patch.object(tutor, "F_DENSE", Path(tempfile.mkdtemp()) / "w")
        self.p.start()

    def tearDown(self):
        self.p.stop()

    def test_three_levels_in_order(self):
        ans = "CODE: Zeile 2 ruft move auf.\nLOGIK: Erst x 0, dann x 1.\nMODELL: Die Drohne ist ein Zeiger. Wo steht sie?\nMODUS: zügig\nSTEUERUNG: keine\nLERNSTAND:\n- behandelt: Position"
        parts, notes, modus, ctl = tutor.parse_parts(ans)
        self.assertEqual(len(parts), 3)
        self.assertTrue(parts[0].startswith("Zeile 2"))
        self.assertTrue(parts[2].endswith("?"))
        self.assertEqual(modus, "zügig")
        self.assertIsNone(ctl)
        self.assertEqual(notes, ["behandelt: Position"])

    def test_sprechen_fallback_and_control(self):
        parts, _, modus, ctl = tutor.parse_parts("SPRECHEN: Gute Frage, schau auf Zeile drei.\nSTEUERUNG: pause")
        self.assertEqual(parts, ["Gute Frage, schau auf Zeile drei."])
        self.assertEqual(modus, "normal")
        self.assertEqual(ctl, "pause")

    def test_skip_and_missing_level(self):
        self.assertEqual(tutor.parse_parts("SKIP")[0], [])
        parts = tutor.parse_parts("CODE: a b c.\nMODELL: d e f?")[0]
        self.assertEqual(parts, ["a b c.", "d e f?"])

    def test_placeholder_levels_not_spoken(self):
        parts = tutor.parse_parts("CODE: Dein or braucht zwei Vergleiche.\nLOGIK: (nicht nötig)\nMODELL: entfällt")[0]
        self.assertEqual(parts, ["Dein or braucht zwei Vergleiche."])

    def test_density_limits_words(self):
        tutor.F_DENSE.write_text("20")
        long = " ".join("Wort%d." % i for i in range(60)) + " Wo?"
        parts = tutor.parse_parts("CODE: " + long)[0]
        self.assertLessEqual(len(parts[0].split()), 21)
        self.assertTrue(parts[0].endswith("Wo?"))


class IntentAndTranscriptTest(unittest.TestCase):
    def test_local_intents(self):
        self.assertEqual(tutor.local_intent("Weiter."), "weiter")
        self.assertEqual(tutor.local_intent("Lass mich kurz selbst überlegen."), "pause")
        self.assertEqual(tutor.local_intent("Langsamer."), "langsamer")
        self.assertIsNone(tutor.local_intent("Warum brauche ich hier eine Schleife?"))
        self.assertIsNone(tutor.local_intent("Erklär mir das nochmal an meinem aktuellen Code."))

    def test_hallucinations_dropped(self):
        self.assertIsNone(tutor.clean_transcript("\n [MUSIK]"))
        self.assertIsNone(tutor.clean_transcript("Untertitel im Auftrag des ZDF, 2020"))
        self.assertIsNone(tutor.clean_transcript("   "))
        self.assertEqual(tutor.clean_transcript("\n Erklär mir die zweite Zeile."), "Erklär mir die zweite Zeile.")


class SpeakableTest(unittest.TestCase):
    def test_symbols_become_speech(self):
        t = tutor.speakable("pro Zelle: harvest → Boden prüfen; a = 3 und x == 0")
        self.assertNotIn("→", t)
        self.assertNotIn(";", t)
        self.assertIn("dann", t)
        self.assertIn("x gleich 0", t)
        self.assertIn("a ist 3", t)


class DictationTest(unittest.TestCase):
    def test_dictation_dropped(self):
        ans = ("CODE: Letzter Versuch. In main.py genau diese Zeilen tippen, ohne selbst umzudenken. max gleich "
               "get world size Klammer auf Klammer zu. Leerzeile. while True Doppelpunkt.\n"
               "MODELL: In Zeile 4 bewegst du die Drohne nach Norden. Was passiert in Zeile 5?")
        parts = tutor.parse_parts(ans)[0]
        self.assertEqual(len(parts), 1)
        self.assertTrue(parts[0].startswith("In Zeile 4"))

    def test_names_readable(self):
        t = tutor.speakable("Nutze get_world_size() und Entities.Carrot")
        self.assertIn("get world size", t)
        self.assertNotIn("Entities", t)


class SignalsAndContextTest(unittest.TestCase):
    def test_wipe_detected(self):
        now = time.time()
        hist = [(now - 100, "while True:\n\tmove(North)\n\tharvest()"), (now - 50, "")]
        sig = tutor.learning_signals(hist, now)
        self.assertEqual(sig["wipes_5min"], 1)
        self.assertEqual(sig["changes_5min"], 2)
        self.assertAlmostEqual(sig["minutes_since_change"], 0.8, places=1)

    def test_said_context_interrupted(self):
        tutor._last_said.clear()
        tutor._last_said.update(text="eins zwei drei vier fünf sechs sieben acht neun zehn", start=100.0, dur=10.0, cut=105.0)
        ctx = tutor.said_context(200.0)
        self.assertIn("UNTERBROCHEN", ctx)
        self.assertIn("5 von 10", ctx)
        tutor._last_said["cut"] = None
        self.assertIn("vollständig", tutor.said_context(200.0))


if __name__ == "__main__":
    unittest.main()
