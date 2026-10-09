# The Farmer Was Replaced – Faktenliste (nur ./docs)

## 1. Kartenrand-Verhalten der Drohne
- Drohne bewegt sich über den Farmrand und wird auf die gegenüberliegende Seite versetzt (Wrap-around) (docs/unlocks/expand_1.md).
- `move(North)` bewegt ein Feld nach Norden; am Rand erscheint sie auf der Gegenseite (docs/unlocks/expand_1.md).
- `move()` benötigt eine Richtung; Konstanten: `North, East, South, West` (docs/unlocks/expand_1.md).
- `move()` gibt `True` bei Erfolg zurück, `False` wenn blockiert (z. B. Hecke) (docs/unlocks/mazes.md).
- `get_world_size()` gibt die Seitenlänge der quadratischen Farm zurück (docs/unlocks/expand_2.md).
- Startposition (0,0); x +1 pro `East`, y +1 pro `North` (docs/unlocks/senses.md).

## 2. Entities & Grounds: Grass, Bush, Tree, Carrot
- Zustandsabfragen: `get_entity_type()` (Entität unter Drohne, sonst `None`), `get_ground_type()` (Boden) (docs/unlocks/senses.md).
- Namespaces: `Entities.*` (Pflanzen), `Grounds.*` (Böden), `Items.*` (docs/unlocks/carrots.md).
- **Grass** (`Entities.Grass`): wächst automatisch, muss nicht gepflanzt werden (docs/unlocks/plant.md); Ernte gibt Heu `Items.Hay` (docs/first_program.md).
- **Bush** (`Entities.Bush`): anfangs einzige pflanzbare Pflanze via `plant(Entities.Bush)`, liefert Holz (docs/unlocks/plant.md); pflanzbar auf Gras oder Ackerboden (docs/unlocks/trees.md).
- **Tree** (`Entities.Tree`): liefert je 5 Holz; pflanzbar auf Gras oder Ackerboden (docs/unlocks/trees.md).
- Tree-Wachstumszeit verdoppelt sich pro direkt benachbartem Baum (N/O/W/S) → bis 2^4 = 16x langsamer (docs/unlocks/trees.md).
- **Carrot** (`Entities.Carrot`): `plant()` erst nach Pflügen; `till()` macht Boden zu `Grounds.Soil` (docs/unlocks/carrots.md).
- Erneutes `till()` ändert `Grounds.Soil` zurück zu `Grounds.Grassland` (docs/unlocks/carrots.md).
- `plant(Entities.Carrot)` kostet Holz und Heu, die automatisch abgezogen werden (docs/unlocks/carrots.md).
- Exakte Karotten-Höhe steht nicht in ./docs (nur Verweis auf nicht vorhandene Seite objects/carrot) (docs/unlocks/carrots.md).
- `clear()` setzt die Farm auf nur Gras zurück und setzt die Drohnenposition zurück (docs/unlocks/plant.md).
- Polykultur: Gras, Busch, Baum, Karotte geben Mehrertrag mit korrektem Begleiter (docs/unlocks/polyculture.md).
- Begleiter ∈ {`Entities.Grass`, `Bush`, `Tree`, `Carrot`}, immer ≠ Pflanze selbst, Position ≤3 Züge entfernt (außer eigener) (docs/unlocks/polyculture.md).
- `get_companion()` → `(Entity, (x,y))` oder `None` (docs/unlocks/polyculture.md).
- Ertragsmultiplikator = 5 vor Polykultur-Freischaltung, verdoppelt sich pro Upgrade (docs/unlocks/polyculture.md).

## 3. Abweichungen von normalem Python (docs/scripting/*)
- Syntax ähnelt Python; Sprache wird schrittweise freigeschaltet (docs/first_program.md).
- Alle Zahlen sind Fließkommazahlen, daher ist jede Arithmetik Fließkomma (docs/scripting/operators.md).
- `//` ist definiert als Abrunden (floor) nach der Division (docs/scripting/operators.md).
- Operatoren: arithm. `+,-,*,/,//,%,**`; Vergleich `==,!=,<=,>=,<,>`; boolesch `not,and,or` (docs/scripting/operators.md).
- `<=,>=,<,>` nur auf Zahlen; `==`,`!=` auf alle Werte (docs/scripting/operators.md).
- `==` prüft Gleichheit, `=` weist zu (nicht verwechseln) (docs/scripting/variables.md).
- Zuweisungsoperatoren `+=,-=,*=,/=,%=` (kein `**=` genannt) (docs/scripting/variables.md, docs/scripting/operators.md).
- `for` ist foreach wie in Python; Sequenzen: Ranges, Listen, Tupel, Dictionaries, Sets (docs/scripting/for.md).
- Scopes „grundsätzlich wie in Python"; `global` nötig, um Globals zu schreiben (docs/scripting/scopes.md).
- Schleifen/Verzweigungen erzeugen keinen eigenen Scope (docs/scripting/scopes.md).
- `def` wirkt wie Zuweisung → Definition muss vor Aufruf stehen (docs/scripting/functions.md).
- Funktionen sind Werte; Standardargumente möglich (docs/scripting/functions.md).
- Listen: Referenzsemantik, Methoden `append/remove/insert/pop`, `len()` (docs/scripting/lists.md).
- Dictionaries und Sets sind ungeordnet, keine Iterationsreihenfolge garantiert (docs/scripting/dicts.md, docs/scripting/sets.md).
- `{}` erzeugt leeres Dictionary; `set()` erzeugt leeres Set (docs/scripting/sets.md).
- Tupel sind immutable und als Dict-Schlüssel nutzbar (docs/scripting/tuples.md).
- `None` existiert; Funktionen ohne `return` liefern `None` (docs/unlocks/senses.md).
- Endlosschleifen frieren nicht ein (Ausführungsverzögerungen) (docs/scripting/while.md).
- `import` führt Datei einmal aus und cached sie danach; `if __name__ == "__main__":`-Muster (docs/scripting/import.md).
- `print()` schreibt in die Luft + Ausgabeseite; `quick_print()` nur ins Fenster (docs/scripting/debug.md).
- Kommentar vor `def` wird Teil des Hover-Tooltips (docs/scripting/comments.md).

## 4. Was die Unlocks bringen
- **expand_1**: Farm wächst; `move()` mit `North/East/South/West`; Bewegung über den Rand wrappt (docs/unlocks/expand_1.md).
- **expand_2**: quadratisches Gitter; `for`-Schleife; `get_world_size()` (docs/unlocks/expand_2.md).
- **senses**: `get_pos_x/y()`, `num_items()`, `get_entity_type()`, `get_ground_type()`, `num_unlocked()`, `None` (docs/unlocks/senses.md).
- **operators**: schaltet Operatoren frei (`<unlock=operators>` im Inhaltsverzeichnis) (docs/home.md, docs/scripting/operators.md).
- **carrots**: Karotten pflanzbar; `till()`/`Grounds.Soil`/`Grounds.Grassland`; Kosten Holz+Heu (docs/unlocks/carrots.md).
- **trees**: Bäume pflanzbar, je 5 Holz, Abstands-Wachstumsregel (docs/unlocks/trees.md).
- **speed**: doppelte Ausführungsgeschwindigkeit; schaltet `if` und `can_harvest()` frei (docs/unlocks/speed.md).
