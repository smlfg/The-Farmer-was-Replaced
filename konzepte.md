# Konzeptkarte

Drei Stufen: **offen** (noch erklären) · **mit Hilfe** (kurz erinnern) · **kann ich** (nicht mehr erklären).
Du darfst die Spalte *Stufe* selbst ändern – dein Eintrag gilt. Der Coach stuft nur hoch, nie runter.

**Übungsserie:** 1 Tag(e) in Folge mit mindestens 25 Minuten · heute 480 Minuten

| Konzept | Name | Stufe | Beleg | Seit |
|---|---|---|---|---|
| `variable` | Variable und Zuweisung | kann ich | max = get_world_size(), x = get_pos_x() selbst geschrieben (BaumKarotten) | 2026-10-09 |
| `vergleich` | Vergleich (==, !=, <, >) | kann ich | get_ground_type() == Grounds.Grassland in vielen Dateien korrekt | 2026-10-09 |
| `zuweisung_vs_vergleich` | Zuweisung = gegen Vergleich == | mit Hilfe | Coach erklärte x, y = 0, 0 ist Zuweisung (Vormittag) | 2026-10-09 |
| `if_else` | Bedingung if / elif / else | kann ich | if/else in BaumKarotten, Kürbis, probleme selbst geschrieben | 2026-10-09 |
| `while` | while-Schleife | kann ich | while True und while (get_pos_x() < ...) selbst geschrieben | 2026-10-09 |
| `for_range` | for-Schleife mit range | kann ich | for j in range(max) in BaumKarotten, BigKürbis | 2026-10-09 |
| `verschachtelte_schleifen` | Verschachtelte Schleifen | mit Hilfe | Move.py/BigKürbis mit Coach-Hilfe; innere/äußere Rolle noch wackelig | 2026-10-09 |
| `funktion_def` | Eigene Funktion mit def | kann ich | def do() in BaumKarotten, per import aufgerufen | 2026-10-09 |
| `parameter` | Parameter einer Funktion | mit Hilfe | check(max) in BigKürbis | 2026-10-09 |
| `rueckgabewert` | Rückgabewert mit return | mit Hilfe | return move(East) unklar; field_ok gibt True/False zurück | 2026-10-09 |
| `aufruf_klammern` | Funktion aufrufen mit Klammern | mit Hilfe | get_pos_x ohne Klammern verglichen, nach Hinweis korrigiert | 2026-10-09 |
| `bool` | Wahrheitswerte True / False | mit Hilfe | fieldok() liefert True/False; Full += fielddo() mit None | 2026-10-09 |
| `modulo` | Rest mit % | kann ich | x % 2 == 0 and y % 2 == 0 selbst abgeleitet (Schachbrett) | 2026-10-09 |
| `and_or_not` | Logik and / or / not | kann ich | x % 2 == 0 and y % 2 == 0 selbst abgeleitet | 2026-10-09 |
| `zaehler` | Zähler und +=  | mit Hilfe | counter += 1 in zweizwei; zählt Runden statt Felder | 2026-10-09 |
| `liste` | Liste [] | mit Hilfe | checklist = [] in eswirdbesser; in Funktion neu zugewiesen | 2026-10-09 |
| `tupel` | Tupel (x, y) | mit Hilfe | checklist.append((x, y)) in eswirdbesser | 2026-10-09 |
| `index` | Index liste[i] | mit Hilfe | checklist[0][1] – x und y vertauscht | 2026-10-09 |
| `append` | Liste erweitern mit append | mit Hilfe | checklist.append((x, y)) in eswirdbesser | 2026-10-09 |
| `len` | Länge mit len | mit Hilfe | range(len(checklist)) in eswirdbesser | 2026-10-09 |
| `global` | Geltungsbereich und global | offen | Fehler 20:27: checklist gelesen, bevor zugewiesen (ernte) | 2026-10-09 |
| `import` | Andere Datei importieren | kann ich | import BaumKarotten, BaumKarotten.do() aufgerufen | 2026-10-09 |
| `position` | Position der Drohne (get_pos_x/y) | kann ich | get_pos_x()/get_pos_y() selbst für Positionen genutzt | 2026-10-09 |
| `print_debug` | Ausgeben zum Prüfen (print) | kann ich | print(counter), print(checklist) selbst eingesetzt | 2026-10-09 |
