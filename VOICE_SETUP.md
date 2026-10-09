# Voice / Push-to-talk – experimenteller Branch

Dieses Feature ist noch nicht mit laufendem Spiel auf dem Ziel-Mac getestet.

## Build (auf dem Mac)

```bash
swiftc -O ptt.swift -o "$HOME/.tfwr-tutor/ptt"
swiftc -O ptt_transcribe.swift -o "$HOME/.tfwr-tutor/ptt-transcribe"
"$HOME/.tfwr-tutor/ptt"
```

Standardtaste: **rechte Wahltaste / Right Option** (macOS-Keycode 61); kein Fokuswechsel. Die Taste wird *mitgehört*, nicht blockiert. Falls das Spiel die rechte Wahltaste belegt, Taste im Quelltext bzw. `TUTOR_PTT_KEYCODE` ändern.

Vorher macOS **Mikrofon**, **Spracherkennung** und **Eingabeüberwachung/Bedienungshilfen** für die ausführende App/Binary genehmigen. Welche Berechtigungen tatsächlich nötig sind, hängt von Signierung und macOS-Version ab. Lokale Transkription über Apple Speech ist nur möglich, wenn `de-DE` auf diesem Rechner als On-Device-Sprache unterstützt wird.

Das Aufnahme-Helperprogramm legt Ereignisse in `~/.tfwr-tutor/ptt-events.jsonl` und die jüngste WAV unter `~/.tfwr-tutor/ptt-recording.wav` an. Es ist ein Integrationsbaustein; bisher wird es nicht automatisch von `tutor.py` gestartet. Deshalb ist die vollständige Voice-Schleife noch **nicht fertig**.

### Sicherheits- und Testcheck

- TTS sofort beim Tastendruck unterbrechen; laufende/veraltete Modellantwort verwerfen
- Erst aufnehmen, nachdem Startsignal verklungen ist; nach Aufnahme-Ende Schlussignal
- Transkript nur bei tatsächlichem Sprachinhalt an `answer_in.txt`/aktive Pi-Sitzung geben
- Während Aufnahme/Transkription keine automatischen Antworten sprechen
- Auf Spielende/Daemon-Ende AudioEngine stoppen und Mikrofon freigeben
- Einmal Test im Vollbild, einmal bei bereits laufender TTS, einmal bei leerer Aufnahme
- Den tatsächlich gesprochenen Anteil zur laufenden Erklärung speichern, statt abgeschnittene Texte als vollständig gesprochen zu markieren

**Bis zum erfolgreichen Integrationstest nicht als fertig bezeichnen.**

## Verknüpfung mit tutor.py (Feature-Branch)

`tutor.py` liest nun die PTT-Ereignisse automatisch während einer Spielsitzung, unterbricht die TTS und reicht das offline transkribierte Ergebnis als `ANTWORT DES LERNENDEN` an **dieselbe Pi-Sitzung** weiter.

**Wichtig:** Der Hotkey-Listener muss zurzeit separat ausgeführt werden; `install` richtet ihn nicht ein. `main` bleibt unverändert. Nicht als produktionsreif ansehen.

### Manueller End-to-End-Test

1. `mkdir -p ~/.tfwr-tutor` und beide Swift-Binaries wie oben bauen (bitte Buildfehler melden).
2. Im ersten Terminal `~/.tfwr-tutor/ptt` starten; Systemberechtigungen prüfen.
3. Im zweiten Terminal `python3 tutor.py run` ausführen und das Spiel öffnen.
4. Während der Tutor spricht die rechte Option-Taste halten, eigene Frage sprechen und loslassen.
5. `python3 tutor.py log` beobachten: Down/Up → Transkript → Pi → TTS. Danach Frage zum aktuellen Code prüfen.
6. Unverständliche/leere Aufnahme, Vollbild, Spielende und Wiederstart testen.

Bekannte Grenzen: Es gibt bislang keine automatische Einrichtung des PTT-Listeners als LaunchAgent, keine abgesicherte Signierung/Berechtigungsführung und keine tatsächliche Erfassung des bereits gesprochenen Wortanteils. Der Kontext enthält stattdessen den vollständigen *unterbrochenen* Sprechtext als möglicherweise nur teilweise gehört.
