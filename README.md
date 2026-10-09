# The Farmer Was Replaced — Local Learning Companion

Ein gesprochener Python-Tutor für *The Farmer Was Replaced* auf einem MacBook Pro M3 Max.
**Spiel öffnen → Tutor ist dabei.** Er stellt sich beim Start einmal kurz vor und ist dann still. Er spricht nur,
wenn du ihn fragst (Sprechtaste) oder wenn dein Code beim Ausführen einen Fehler wirft (aus `output.txt`
des Spiels). Stimme: Piper „Thorsten“. Du schreibst den Code **selbst**. Eigene Impulse wie früher:
`TUTOR_PROACTIVE=1`.

Implementierungsauftrag: [CLAUDE.md](CLAUDE.md).

## Bedienung im Spiel (ohne Fensterwechsel)

| Aktion | Wie |
|---|---|
| Sprechen | **rechte ⌥-Taste halten** → „Tink“ → sprechen → loslassen → „Pop“ |
| Tutor unterbrechen | Sprechtaste drücken: laufende Sprache stoppt sofort, wartende Erklärungen entfallen |
| Denkpause | sagen: „Lass mich kurz selbst überlegen“ oder „Pause“ – bleibt, bis du „Weiter“ sagst |
| Weiter | „Weiter“ |
| Weniger/mehr pro Nachricht | „Langsamer“ / „Schneller“ (Informationsmenge, nicht Sprechtempo) |
| Alles andere | normale Frage, z. B. „Erklär mir das nochmal an meinem aktuellen Code“ |

⌥ + Taste (z. B. ⌥L für @) bleibt nutzbar: Die Aufnahme startet erst nach 0,25 s Halten und bricht ab,
sobald eine weitere Taste kommt. Andere Taste: `TUTOR_PTT_KEY` (Keycode, z. B. 54 = rechte ⌘).

## Befehle im Terminal (optional)

Im Repo-Ordner:

```bash
python3 tutor.py status
python3 tutor.py pause        # bleibt pausiert, bis resume – der Wächter hebt sie nie auf
python3 tutor.py resume
python3 tutor.py now          # sofort erklären
python3 tutor.py still        # nur die laufende Sprache beenden
python3 tutor.py antwort "bei x 1, y 2"   # Antwort auf seine Vorhersagefrage (Alternative zur Sprechtaste)
python3 tutor.py unlocked "trees"         # Freischaltung melden (gilt als „nicht belegt“)
python3 tutor.py install      # Autostart einrichten (einmalig)
python3 tutor.py uninstall    # Autostart komplett aus
python3 tutor.py log          # Log mitlesen
```

## Startverhalten

- LaunchAgent `com.smlfg.tfwr-tutor` startet beim Login die Starter-App `~/Applications/TFWR Tutor.app`,
  die `tutor.py run` als Kindprozess ausführt (keine offenen Terminals, eine Instanz per Datei-Lock,
  Neustart frühestens nach 60 s).
- Ohne Spiel: alle 3 s ein `pgrep` auf das echte Spiel-Binary (`TheFarmerWasReplaced.app/Contents/MacOS/…`,
  nicht Steam/Overlay) – keine Modellaufrufe, Mikrofon aus.
- Spiel erkannt → genau eine Sitzung: Pi-Prozess, Sprechtaste, Beobachtung.
- Spiel beendet → Aufnahme und Sprache stoppen, Mikrofon frei, Pi beendet; Lernstand und Notizbuch bleiben
  gespeichert und werden beim nächsten Start geladen.

## macOS-Berechtigungen (einmalig, alle für „TFWR Tutor“)

Systemeinstellungen → Datenschutz & Sicherheit:

1. **Bildschirm- & Systemaudioaufnahme**: „+“ → `~/Applications/TFWR Tutor.app`. Ohne: Tutor läuft, aber ohne Bild,
   und behauptet nichts Visuelles.
2. **Eingabeüberwachung**: „+“ → dieselbe App. Ohne: Sprechtaste reagiert nicht (Log: „Eingabeüberwachung fehlt“).
3. **Mikrofon**: macOS fragt beim ersten Drücken der Sprechtaste.

Wird die App neu gebaut (nur wenn `Info.plist` fehlt/veraltet), ändert sich ihre Signatur: Einträge dann mit „−“
entfernen und neu hinzufügen.

## Wie er arbeitet

```
Spiel läuft ─► tutor.py (Wächter, lokal)
                 ├─ liest main.py/save.json (nur lesend; das Spiel speichert beim Tippen)
                 ├─ Screenshot nur vom Spielfenster (screencapture -l)
                 ├─ Sprechtaste: ptt.swift (nur mithören) → ffmpeg → whisper-cli small, deutsch, lokal
                 └─ Pi im RPC-Modus (ohne Werkzeuge, ein Gesprächskontext pro Spielsitzung)
                        └─ Antwort: DIAGNOSE, HILFE, ZIEL/ANSATZ/REAKTION, CODE/LOGIK/MODELL, LERNSTAND
               Piper Thorsten ◄─ nur der Lehrtext wird gesprochen
```

- **Takt**: ein Snapshot → bis zu drei Teile (CODE, LOGIK, MODELL), etwa einer pro Minute (gemessen: ~62 s).
  Die nächste Analyse wird vorausgerechnet. Abstand je Modus: festgefahren 45 s, normal 60 s, zügig 90 s.
- **Didaktik** ([prompt.md](prompt.md)): Diagnose der Ebene (Aufgabenverständnis … Effizienz), Weg vom Problem
  zum Programm, Hilfestufen 1–4, nie ungefragt die Lösung.
- **Lehransätze** ([prompts/ansaetze.md](prompts/ansaetze.md)): 9 Bausteine (Ablauf, Analogie, Zerlegung,
  Beispiel, Vorhersage, Vergleich, Rückwärts, Fading, Erklären lassen), adaptiv gewählt; gemerkt im
  Tutor-Notizbuch `~/.tfwr-tutor/notizbuch.json` (Ziel, letzter Ansatz, Reaktion, offene Frage).
- **Lernstand** ([progress.md](progress.md)): pro Konzept *erklärt* → *mit Hilfe* → *selbstständig*, steigt nur auf.
- **Unterbrechung**: Der Tutor merkt sich, was er gesagt hat und wo du unterbrochen hast, und bezieht Rückfragen darauf.

**Daten in die Cloud:** Screenshots, Spielcode und Lernstand gehen über Pi an MiniMax (`minimax/MiniMax-M3`).
Spracherkennung, Stimme und Steuerung bleiben lokal. Ein lokales Vision-Modell war zu langsam
(362 s statt 28 s, Format gebrochen): [docs/LOCAL_MODEL_EVAL.md](docs/LOCAL_MODEL_EVAL.md).

## Lokaler Fallback ohne Cloud-API

**Normalbetrieb:** Pi/MiniMax bleibt der ausführliche Tutor. Lehnt die API eine Anfrage ab,
bricht Pi ab oder antwortet länger als 40 Sekunden nicht, wechselt der Tutor automatisch
zur lokalen Lernbegleitung. Nach 180 Sekunden versucht er die Cloud erneut.

**Lokal:** Zuerst wird ein Ollama-Modell nur unter `127.0.0.1` angesprochen
(Standard: `qwen3:8b`). Ist Ollama nicht erreichbar oder antwortet das Modell nicht
rechtzeitig, gibt ein kleines regelbasiertes Modul eine einzelne konkrete Denkhilfe anhand
des Codes und des gespeicherten Lernziels. Es löst die Aufgabe nicht automatisch.
Die lokale Variante kann Code, aber **keine Screenshots** interpretieren.
Es findet dabei keine Netzverbindung außerhalb des Macs statt.

Manueller Offlinebetrieb (keine Cloud-Anfrage, auch beim Start nicht):

```bash
TUTOR_OFFLINE=1 python3 tutor.py run
```

Optional, vor dem Start `ollama serve` und `ollama pull qwen3:8b` ausführen.
Falls Ollama nicht installiert ist, funktioniert trotzdem der regelbasierte Modus.

| Einstellung | Standard | Zweck |
|---|---|---|
| `TUTOR_OFFLINE` | `0` | `1` erzwingt lokale Begleitung |
| `TUTOR_API_FAIL_TIMEOUT` | `40` | Sekunden bis zum automatischen Wechsel |
| `TUTOR_API_RETRY` | `180` | Sekunden bis zum nächsten Cloud-Versuch |
| `TUTOR_LOCAL_MODEL` | `qwen3:8b` | Lokales Ollama-Modell |
| `TUTOR_LOCAL_URL` | `http://127.0.0.1:11434/api/generate` | Nur Loopback erlaubt |
| `TUTOR_LOCAL_TIMEOUT` | `25` | Sekunden bis zur regelbasierten Hilfe |

Die fokussierte Datei wird aus dem Änderungszeitpunkt der gespeicherten Spiel-Dateien
ermittelt. Das ist eine **Heuristik**, keine verlässliche Erkennung des sichtbaren Editor-Tabs.
Der bisherige Cloud-Tutor und seine ausführliche Didaktik bleiben unverändert.

## Konfiguration

Alles per Umgebungsvariable `TUTOR_<NAME>` (im LaunchAgent unter `EnvironmentVariables`), siehe `CFG` oben in
`tutor.py`: `INTERVAL`, `GAP_NORMAL`, `PREFETCH`, `PTT_KEY`, `PTT_HOLD`, `MIC`, `MODEL`, `WHISPER_MODEL` …
Zustand und Logs: `~/.tfwr-tutor/` (`tutor.log`, `spoken.txt`, `notizbuch.json`, `sessions/`).

## Tests

```bash
/usr/bin/python3 -m unittest discover tests
```

60 Unit-Tests ohne Netz, Spiel oder Ton (Parsing, Lernstand, Sprachbefehle, Whisper-Filter, Pi-Ereignisse, Takt).

Praxis-Tests, die Hardware oder Netz brauchen (einzeln starten):

```bash
/usr/bin/python3 tests/smoke_speech.py
```
```bash
/usr/bin/python3 tests/smoke_pi.py
```

## Stand der Prüfung (ehrlich)

| Geprüft am laufenden Spiel | Ergebnis |
|---|---|
| Spiel erkannt, Code live gelesen | ja (Datei aktueller als der Screenshot) |
| Screenshot nur Spielfenster | ja, nach Freigabe für TFWR Tutor |
| Hörbare Erklärung, ~1/min | ja, gemessen 62 s Abstand |
| Sprechtaste → Frage → Antwort mit Code-Kontext | ja (12:55 und 13:00, nach Fixes) |
| Pause/Weiter per Sprache | eingebaut und getestet (Unit), am Spiel noch nicht ausdrücklich vorgeführt |
| Spielende → alles stoppt, Neustart mit Lernstand | **noch nicht** am echten Spielende getestet |

Bekannte Grenzen: Das Modell hält „höchstens eine Frage“ nicht immer ein; Länge wird im Code gekappt,
Fragenzahl nicht. Lokales Modell zu langsam.
