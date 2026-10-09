# Erfahrungsbericht: opencode go als Subagent (2026-10-09)

> **Abgrenzung:** Dieser Branch gehört **nicht** zum Tutor. Er hält fest, wie sich `opencode run`
> (opencode go, Modell `opencode-go/deepseek-v4.1-flash`, opencode 1.18.30) als Implementierungs-Subagent
> von Claude Code verhalten hat, während der Tutor gebaut wurde. Thema: CLI-/MCP-Agenten-Entwicklung
> (Delegation, Harness, Watchdog) – Input für den HAI-Stack, nicht für das Spiel.

## Was delegiert wurde

| Zeit | Auftrag | Form | Ergebnis |
|---|---|---|---|
| 11:20 | Doku-Fakten aus Spieldateien | 1 Lauf, liest außerhalb cwd | ✗ `external_directory` im Nicht-Interaktiv-Modus auto-abgelehnt, Lauf endet still mit exit 0 |
| 11:25 | dasselbe mit Kopie der Doku im cwd | 1 Lauf | ✓ 58 Zeilen Faktenliste, Quellen je Zeile |
| 11:46 | 5 Kritikpunkte, je ein Git-Worktree/Branch | 5 parallel | ✓ 4/5 mit Tests und Commit (robust 13, tests 17, feedback 11, smoke real) · ✗ local-model: wieder `external_directory` (Pi-Bundle lesen) → aufgegeben ohne Bericht |
| 12:03 | kleiner Fix `should_speak` + Test | 1 Lauf, kurzer Brief | ✓ ~2 min, sauberer Diff, Tests grün |
| 12:15 | drei Ebenen pro Snapshot (langer Brief, bestehende Dateien) | 1 Lauf | ✗ >20 min keine Dateiänderung, abgebrochen |
| 12:28 | drei Ebenen + adaptives Coaching (langer Brief) | 1 Lauf | ✗ >7 min nichts, abgebrochen |
| 12:59 | Lehransätze (langer Brief) | 1 Lauf | ✗ 4,5 min, 0,1 % CPU, keine Ausgabe, abgebrochen |
| 13:04 | nur neue Datei `prompts/ansaetze.md` | 1 Lauf, kurz | ✓ **18 s**, brauchbar |
| 13:05 | nur Abschnitt in bestehender `prompt.md` | 1 Lauf, kurz | ✗ 180 s nichts, abgebrochen |

Bilanz: 7 von 13 Einzelaufträgen erfolgreich (ein weiterer Lauf um 11:38 wurde beim Repo-Umzug von mir abgebrochen, nicht gezählt); alle Fehlschläge **still** (kein Fehler, kein Bericht).

## Beobachtete Muster (belegt)

1. **Berechtigungen:** Im Nicht-Interaktiv-Modus wird `external_directory` automatisch abgelehnt. Der Agent
   gibt dann auf und beendet sich mit **exit 0** – von außen sieht das wie Erfolg aus.
2. **Hänger:** Prozess lebt, CPU ~0 %, `opencode run` schreibt stdout erst am Ende → von außen nicht von
   „arbeitet“ zu unterscheiden. Im Log des Laufs von 13:05: `init` → **3 min** → `session created` →
   nur der Titel-Aufruf (`muse-spark-1.3-contributor-free`), **kein** Aufruf des eigentlichen Modells.
   `edit` war erlaubt (`action=allow`) – keine Berechtigungsabfrage als Ursache.
3. **Was zuverlässig lief:** kurze Briefs; neue Dateien; parallele Worktrees mit je eigenem Branch.

## Vermutungen (nicht verifiziert)

- Blockade beim Sitzungsstart (3 min bis `created`), evtl. Sperre auf `~/.local/share/opencode/opencode.db`
  durch zuvor per `pkill` beendete Läufe oder Anbieter-Latenz bei opencode go.
- Lange Briefs mit Lesen/Ändern bestehender Dateien verstärken das; Ursache offen.

## Was sich als Arbeitsweise bewährt hat

- Ein Auftrag = ein Worktree + Branch; Claude prüft Diff und Tests, erst dann Merge.
- Briefs kurz halten (eine Datei, ein Ziel, DoD als Befehl).
- Daten ins cwd kopieren statt außerhalb lesen zu lassen.
- **Fortschritt an Dateiänderungen messen**, nicht an stdout; nach ~3 min ohne Änderung abbrechen und
  selbst übernehmen.

## Task (offen) – für den CLI/MCP-Stack

**Ziel:** Delegation an `opencode run` so absichern, dass stille Fehlschläge sichtbar werden.

- [ ] Hänger reproduzieren: kurzer Brief, der eine bestehende Datei ändert; Log mit `--log-level DEBUG`
      (falls verfügbar) und `lsof` auf `opencode.db` während des Hängers.
- [ ] Prüfen, ob abgebrochene Läufe Sperren hinterlassen (Start direkt nach `pkill` vs. nach Pause).
- [ ] Kleiner Watchdog-Wrapper (Glue, kein eigenes Framework): startet `opencode run`, beobachtet
      Dateiänderungen im Worktree + Log-Zeilen des Laufs, bricht nach N s Stillstand ab, meldet
      `BLOCKED` statt exit 0; bei `external_directory`-Ablehnung ebenfalls `BLOCKED`.
- [ ] Ergebnis als Evidenz an die HAI-Mission (`hai_checkpoint`), Entscheidung: opencode go als Default-Worker
      behalten, nur für kurze Aufträge nutzen, oder Alternative (cao / agent-collab) prüfen.

DoD: Ein absichtlich hängender Lauf wird binnen 3 min als `BLOCKED` gemeldet; ein normaler Lauf liefert
Diff + Testausgabe wie bisher.
