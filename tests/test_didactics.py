import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("TUTOR_STATE", tempfile.mkdtemp())
import tutor  # noqa: E402


class ProgressTiersTest(unittest.TestCase):
    def setUp(self):
        self.f = Path(tempfile.mkdtemp()) / "progress.md"
        self.p = mock.patch.object(tutor, "PROGRESS", self.f)
        self.p.start()

    def tearDown(self):
        self.p.stop()

    def test_only_upgrades(self):
        tutor.save_progress(["erklärt: Schleife"])
        tutor.save_progress(["mit Hilfe: Schleife"])
        tutor.save_progress(["erklärt: Schleife"])  # kein Abstieg
        text = self.f.read_text()
        self.assertIn("- mit Hilfe: Schleife", text)
        self.assertNotIn("erklärt: Schleife", text)
        tutor.save_progress(["selbstständig: Schleife"])
        self.assertIn("- selbstständig: Schleife", self.f.read_text())

    def test_legacy_entries_understood(self):
        self.f.write_text("# Lernstand\n\n- gezeigt: if  (2026-10-09)\n")
        tutor.save_progress(["mit Hilfe: if"])  # gezeigt == selbstständig, nicht absteigen
        self.assertIn("- gezeigt: if", self.f.read_text())

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

    def test_approaches_rotate(self):
        self.assertNotEqual(tutor.approach_for(0), tutor.approach_for(1))
        self.assertEqual(tutor.approach_for(0), tutor.approach_for(len(tutor.APPROACHES)))


if __name__ == "__main__":
    unittest.main()
