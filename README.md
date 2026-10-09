# The Farmer Was Replaced — Local Learning Companion

Projekt: ein lokal laufender, sprachbasierter Python-Lernbegleiter für *The Farmer Was Replaced* auf einem MacBook Pro M3 Max.

## Ziel

Während das Spiel läuft, soll ein Agent (1) das sichtbare Spielfeld beziehungsweise neue Freischaltungen erkennen, (2) den vom Spieler geschriebenen Code lesen und (3) passende Programmierkonzepte auf Deutsch per Text-to-Speech erläutern. Der Spieler schreibt und korrigiert den Code **selbst**.

Lernfokus: Python-Syntax, algorithmische Logik und mentale Modelle – insbesondere die Verallgemeinerung einer starren 3×3-Feldroute zu einem generischen Algorithmus, Schleifen, Zustände, Koordinaten, Randbedingungen sowie spätere Anbauentscheidungen für Weizen, Bäume und Karotten.

## Umsetzung mit Claude Code

Siehe [CLAUDE.md](CLAUDE.md) für den kopierfertigen Implementierungsauftrag. Die erste Version soll bewusst klein sein und nach Möglichkeit vollständig lokal laufen.

**Status:** MVP läuft (Wächter + Pi + Thorsten-TTS), siehe unten.

## Tutor – Betrieb

Gesprochener Programmier-Tutor für „The Farmer Was Replaced“. Spiel öffnen → Tutor ist dabei.

- **Wächter** (`tutor.py`, LaunchAgent): erkennt das echte Spiel-Binary, liest Code + Freischaltungen
  nur lesend aus `save.json`/`*.py`, nimmt Screenshots nur vom Spielfenster (alle ~25 s), ohne Modellaufrufe.
- **Pi** (`pi --mode rpc`, Modell `minimax/MiniMax-M3`, ohne Werkzeuge): ein Gesprächskontext pro Spielsitzung,
  bekommt Screenshot + Code + belegte Doku, antwortet mit Lehrtext.
- **Stimme**: Piper Thorsten via `pycoach-speak` ([mesh-ear-lock](https://github.com/smlfg/mesh-ear-lock)), Fallback `say`.
- **Lernstand**: `progress.md` (behandelt / gezeigt), wird beim nächsten Spielstart wieder geladen.

Daten an Cloud: Screenshots, Spielcode und Lernstand gehen an MiniMax (über Pi). Alles andere bleibt lokal.

## Befehle

```bash
python3 tutor.py install     # Autostart einrichten (einmalig)
python3 tutor.py status
python3 tutor.py pause       # bleibt pausiert, bis resume
python3 tutor.py resume
python3 tutor.py now         # jetzt erklären
python3 tutor.py still       # aktuelle Sprache sofort beenden
python3 tutor.py uninstall   # Autostart komplett aus
```

Einstellbar per Umgebung (`TUTOR_INTERVAL`, `TUTOR_THINK_PAUSE`, `TUTOR_MODEL`, …) – siehe Kopf von `tutor.py`.

## macOS-Berechtigung

Bildschirmaufnahme für den LaunchAgent-Python (`/usr/bin/python3` → Xcode-Python) erlauben,
sonst läuft der Tutor ohne Bild und sagt das auch.
