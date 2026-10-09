# Lehrplan: The Farmer Was Replaced

Täglich 19:00–19:25 Uhr, ein Konzept pro Termin, aufeinander aufbauend. Reihenfolge nach dem Katalog
„Programmiermodelle – Konzepte, die ich wirklich verstehen muss“; was laut [Konzeptkarte](konzepte.md)
schon sitzt (if, while, for, def), ist übersprungen. Jedes Konzept hängt am eigenen Kürbis- und
Navigationsprojekt – keine neuen Dateien. Ab 24.10. weiter mit Uni-Python in Zed.

Der Coach liest diese Tabelle: Er nennt das Tageskonzept beim Start und bezieht Antworten darauf, wenn es passt.
Ändern erlaubt – Datum im Format JJJJ-MM-TT lassen.

| Datum | Konzept | Am eigenen Code |
|---|---|---|
| 2026-10-10 | Wert, Name, Binding | `x = get_pos_x()` merkt sich einen Wert, nicht die Position live |
| 2026-10-11 | Typ, Boolean, Ausdruck gegen Anweisung | `Full += fielddo()`, wenn die Funktion `None` liefert |
| 2026-10-12 | Funktion, Parameter gegen Argument | `check(max)`: Definition gegen Aufruf |
| 2026-10-13 | Rückgabewert (return ist nicht print) | `return move(East)`, `field_ok()` |
| 2026-10-14 | Scope | der `global`-Fehler in `ernte` |
| 2026-10-15 | Liste | `checklist` als Gedächtnis für tote Kürbisse |
| 2026-10-16 | Index | `checklist[0][1]`: x und y vertauscht |
| 2026-10-17 | Tupel | `(x, y)` als unveränderliches Paar |
| 2026-10-18 | Iteration: `for element in liste` gegen `for i in range(len(liste))` | Prüfstein aus dem Katalog |
| 2026-10-19 | while mit Abbruchbedingung | zu einer Koordinate fahren |
| 2026-10-20 | Zustand | Zellen leer, gesät, tot, reif (Denknotiz 9.10.) |
| 2026-10-21 | Algorithmus und Invariante | Säen-Runde, dann Kontrollrunde über die Fehlerliste |
| 2026-10-22 | Debugging | Hypothese über den Zustand bilden, mit `print` prüfen |
| 2026-10-23 | Zeitkomplexität (Gefühl, keine Formeln) | volle Runde n² gegen nur Fehlerliste |
