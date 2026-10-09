import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["TUTOR_STATE"] = tempfile.mkdtemp()  # nie ins echte ~/.tfwr-tutor schreiben
import tutor  # noqa: E402


class ParseTiersTest(unittest.TestCase):
    def test_parse_parts_reads_new_tiers_and_diagnosis(self):
        ans = ("DIAGNOSE: Algorithmus | Beobachtung: nur move | Vermutung: Ablauf fehlt\nHILFE: 2\n"
               "LOGIK: Erst eine Spalte.\nMODUS: normal\nLERNSTAND:\n- mit Hilfe: Spalte zuerst")
        parts, notes, _, _ = tutor.parse_parts(ans)
        self.assertEqual(parts, ["Erst eine Spalte."])
        self.assertEqual(notes, ["mit Hilfe: Spalte zuerst"])


class PiCorrelationTest(unittest.TestCase):
    """Ein verspätetes agent_settled eines abgebrochenen Laufs darf nicht als Antwort gelten."""

    def make_pi(self):
        pi = tutor.Pi.__new__(tutor.Pi)
        pi.events, pi.busy, pi.started, pi.settling, pi.settle_t, pi.req = tutor.queue.Queue(), False, False, False, 0.0, 0
        pi.sent = []
        pi.send = lambda cmd: pi.sent.append(cmd)
        return pi

    def test_stale_settled_after_abort_ignored(self):
        pi = self.make_pi()
        pi.ask("alt", None); pi.events.put({"type": "agent_start"}); pi.poll()
        pi.abort()
        self.assertFalse(pi.ready())
        pi.events.put({"type": "agent_settled"})  # Ende des abgebrochenen Laufs
        self.assertIsNone(pi.poll())
        self.assertTrue(pi.ready())
        pi.ask("neu", None)
        pi.events.put({"type": "agent_settled"})  # ohne agent_start: nicht unsere Antwort
        self.assertIsNone(pi.poll())
        self.assertTrue(pi.busy)
        pi.events.put({"type": "agent_start"}); pi.events.put({"type": "agent_settled"})
        pi.poll()
        self.assertEqual(pi.sent[-1]["type"], "get_last_assistant_text")
        self.assertTrue(pi.busy)  # noch beschäftigt, bis der Text da ist
        pi.events.put({"type": "response", "id": "last", "data": {"text": "SPRECHEN: hallo"}})
        self.assertEqual(pi.poll(), "SPRECHEN: hallo")
        self.assertFalse(pi.busy)

    def test_building_blocks_present(self):
        text = (tutor.HERE / "prompts" / "ansaetze.md").read_text()
        for k in ("ABLAUF", "MODELL_ANALOGIE", "ZERLEGUNG", "BEISPIEL", "VORHERSAGE", "VERGLEICH",
                  "RUECKWAERTS", "FADING", "ERKLAEREN_LASSEN"):
            self.assertIn("## " + k, text)


class NotebookTest(unittest.TestCase):
    def test_parse_and_not_spoken(self):
        ans = ("ZIEL: eine Spalte ernten\nANSATZ: ZERLEGUNG\nREAKTION: hängt an move North\n"
               "OFFENE_FRAGE: keine\nLOGIK: Erst eine Spalte.\nMODUS: normal")
        nb = tutor.parse_notebook(ans)
        self.assertEqual(nb["ansatz"], "ZERLEGUNG")
        self.assertEqual(nb["ziel"], "eine Spalte ernten")
        parts = tutor.parse_parts(ans)[0]
        self.assertEqual(parts, ["Erst eine Spalte."])  # Notizbuch wird nie vorgelesen

    def test_save_load_roundtrip(self):
        d = Path(tempfile.mkdtemp())
        with mock.patch.object(tutor, "STATE", d):
            tutor.save_notebook({"ziel": "x", "ansatz": "VERGLEICH"})
            self.assertEqual(tutor.load_notebook()["ansatz"], "VERGLEICH")
            self.assertIn("VERGLEICH", tutor.notebook_line(tutor.load_notebook()))


if __name__ == "__main__":
    unittest.main()


class OutputClassTest(unittest.TestCase):
    def test_syntax_classified(self):
        self.assertEqual(tutor.output_class("DIAGNOSE: Syntax + Algorithmus | Beobachtung: x"), "syntax")
        self.assertEqual(tutor.output_class("DIAGNOSE: Algorithmus | Beobachtung: x"), "lehre")
        self.assertEqual(tutor.output_class("SPRECHEN: hallo"), "lehre")
