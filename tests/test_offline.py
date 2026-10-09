"""Checks for the local tutor; no microphone, game, Pi or network needed."""
import hashlib
import time
import unittest
from unittest import mock

from offline_tutor import (LocalPi, context_from_observation, focus_from_observation,
                           local_model_reply, simple_hint)

OBS = """BEOBACHTUNG – Anlass: Code/Spielstand geändert
Fokusdatei (jüngste Änderung): eswirdbesser.py
### main.py
```
(leer)
```
### Full.py
```
Ziel: Kürbis
```
### eswirdbesser.py (geändert)
```
checklist = [(4, 2)]
get_pos_x()
```
Tutor-Notizbuch (vorläufig): Ziel: Zu toten Kürbissen fahren; zuletzt Ansatz: keiner"""


class OfflineTutorTest(unittest.TestCase):
    def test_focus_prefers_latest_marker(self):
        self.assertEqual(focus_from_observation(OBS)[0], "eswirdbesser.py")
        self.assertIn("checklist", context_from_observation(OBS)["code"])

    def test_falls_back_to_changed_file(self):
        src = OBS.replace("Fokusdatei (jüngste Änderung): eswirdbesser.py\n", "")
        self.assertEqual(focus_from_observation(src)[0], "eswirdbesser.py")

    def test_goal_and_voice_extracted(self):
        src = OBS.replace("Code/Spielstand geändert",
                          "DER LERNENDE SAGT (gesprochen): „Wie speichere ich x?“")
        ctx = context_from_observation(src)
        self.assertEqual(ctx["goal"], "Zu toten Kürbissen fahren")
        self.assertEqual(ctx["user"], "Wie speichere ich x?")

    def test_local_hint_contextual_without_network(self):
        self.assertIn("Tupel", simple_hint(context_from_observation(OBS)))

    def test_nonlocal_url_refused(self):
        with self.assertRaises(ValueError):
            local_model_reply(context_from_observation(OBS), "qwen3:8b",
                              "https://remote.example.com/api/generate", 2)

    def test_local_ollama_request(self):
        response = mock.MagicMock()
        response.__enter__.return_value = response
        with mock.patch("offline_tutor.urllib.request.urlopen", return_value=response) as request, \
             mock.patch("offline_tutor.json.load",
                        return_value={"response": "Vergleiche dein x mit dem Ziel. Was fehlt?"}):
            msg = local_model_reply(context_from_observation(OBS), "qwen3:8b",
                                    "http://localhost:11434/api/generate", 2)
        self.assertIn("Ziel", msg)
        self.assertIn(b"qwen3:8b", request.call_args.args[0].data)

    def test_offline_when_ollama_missing(self):
        bot = LocalPi(timeout=1)
        with mock.patch("offline_tutor.local_model_reply", side_effect=OSError("offline")):
            bot.ask(OBS)
            for _ in range(100):
                result = bot.poll()
                if result is not None:
                    break
                time.sleep(0.01)
        self.assertIn("Tupel", result)
        self.assertFalse(bot.busy)

    def test_unchanged_code_does_not_trigger_repeat(self):
        bot = LocalPi()
        ctx = context_from_observation(OBS)
        bot.last_signature = hashlib.sha256(
            (ctx["file"] + ctx["code"] + ctx["user"]).encode()).hexdigest()
        bot.ask(OBS)
        self.assertEqual(bot.poll(), "SKIP")

    def test_automatic_continue_does_not_chatter(self):
        bot = LocalPi()
        bot.ask(OBS.replace("Code/Spielstand geändert", "weiter (nur sprechen)"))
        self.assertEqual(bot.poll(), "SKIP")

    def test_abort_discards_old_answers(self):
        bot = LocalPi()
        bot.abort()
        bot.messages.put((0, "SPRECHEN: veraltete Antwort"))
        self.assertIsNone(bot.poll())


if __name__ == "__main__":
    unittest.main()


class RuntimeErrorHintTest(unittest.TestCase):
    def test_scope_error_receives_specific_hint(self):
        obs = OBS.replace("Code/Spielstand geändert",
                          "FEHLER BEIM AUSFÜHREN (Spielausgabe output.txt):\nError: Variable checklist gelesen, bevor ihr ein Wert zugewiesen wurde.")
        ctx = context_from_observation(obs)
        self.assertIn("bevor ihr ein Wert", ctx["error"])
        self.assertIn("Geltungsbereich", simple_hint(ctx))
