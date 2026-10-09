# Claude Code — Build the Farmer Tutor

Du implementierst einen kleinen lokalen Voice-Tutor für *The Farmer Was Replaced* auf meinem MacBook Pro M3 Max. Ich studiere angewandte KI und muss Python, Algorithmen und ihre mentalen Modelle selbst verstehen.

**Arbeite direkt in diesem Repository. Fang mit einem funktionierenden MVP an. Keine überdimensionierte Agentenplattform.**

## Nutzererlebnis

Wenn das Spiel läuft, soll auch der Tutor laufen. Er beobachtet regelmäßig:
1. Das sichtbare Spielfeld und Hinweise auf neue Freischaltungen via Screenshot der Spielregion.
2. Meinen aktuell selbst geschriebenen Spielcode (direkt aus einer zugänglichen Spiel-Datei, falls technisch möglich; sonst über den sichtbaren Editor oder einen ausdrücklich ausgewählten lokalen Export).
3. Veränderungen des Spielfelds, Codes und Freischaltungsstands.

Er erklärt mir daraus auf **Deutsch per lokaler Text-to-Speech** die relevanten Konzepte, möglichst ohne dass ich ständig einen Knopf drücke. Sprachausgabe muss verständlich und kurz sein, keine endlosen Vorträge. Fragen darf er stellen, aber nicht alle zwei Sekunden und nicht dieselbe Frage wiederholen.

## Mein erstes echtes Problem

Ich habe ein 3×3-Spielfeld und aktuell einen starren Bewegungsablauf mit wiederholten Schritten nach oben und zur Seite. Ich möchte daraus selbst einen Algorithmus entwickeln, der jede Zelle besucht, erntet und sät und später auch bei anderen Feldgrößen funktioniert. Im Spiel gibt es Weizen, Bäume und Karotten, später mehr. Erkläre mir daran **Position/Zustand, Koordinaten, Iteration, verschachtelte Schleifen, Invarianten, Randbedingungen, Generalisierung, Funktionen, Bedingungen und Datenstrukturen** — aber liefere mir den fertigen Algorithmus nicht ungefragt.

## Lernregeln

- Konkrete Beobachtung aus meinem Code oder Screenshot → EIN Konzept erklären → EINE prüfbare Frage oder Vorhersage → Raum zum selbst Coden lassen.
- Keine erfundenen TODO-Apps oder theoretischen Ersatzprobleme.
- Nie einfach sagen „Du hast das verstanden“, sondern mit Transfer auf eine zweite reale Codestelle prüfen.
- Zwischen String, Tuple, Objekt, Referenz, Funktion, Rückgabewert und Seiteneffekt klar unterscheiden, aber nur wenn relevant.
- Bei fehlender Evidenz ausdrücklich sagen, was nicht sichtbar ist.
- Auf Wunsch detailliert erklären, standardmäßig maximal 30–80 gesprochene Wörter pro Intervention.
- Keine automatische Veränderung meines Spielcodes, kein Autoplayer.
- Mein Fortschritt wird anhand nachvollziehbarer eigener Vorhersagen, Erklärungen und Änderungen beurteilt, nicht anhand erreichter Spiellevel.

## Technische MVP-Anforderungen

1. Prüfe vor dem Bauen die tatsächliche macOS-Spielinstallation, Prozessnamen, Fenstertitel, Editor-Verfügbarkeit, Screen-Capture-Rechte und mögliche Code-Exportpfade. Erfinde keine APIs oder Spiel-Dateipfade.
2. Lokale, schlanke Pipeline: Fenster/Region-Screenshot → Vision-Modell (Ollama, zuerst ein auf meinem Rechner verfügbares Vision-Modell prüfen) + Code-Text → kurze Tutorantwort → macOS `say` oder andere vorhandene lokale TTS. Bildschirmfreigabe nur für das Spiel; keine heimliche Ganzbildschirm-Aufzeichnung.
3. Beobachtung alle 5–15 Sekunden, Erklärung bei relevanten Änderungen und mit Cooldown gegen Redundanz; manuelle Sofort-Erklärung ermöglichen. Bei pausiertem/geschlossenem Spiel pausieren.
4. State klein halten: letzter Codehash, letzter Bildhash, erkannte Freischaltungen mit Konfidenz, letztes erläutertes Konzept, aktuelle offene Lernfrage. Visuelle Schätzungen nicht als bestätigte Fakten behandeln.
5. Ermögliche zusätzlich den manuellen Befehl „Ich habe X freigeschaltet“, falls die visuelle Erkennung scheitert.
6. Minimale Installation und ein einzelner Startbefehl. Gute Fehlerausgaben für fehlendes Ollama, fehlendes Modell, Screen-Recording-Rechte oder nicht lesbaren Code.
7. Keine externen Cloud-Calls für Spielbilder und Code ohne ausdrückliche Zustimmung.
8. Schreib README mit konkreter macOS-Anleitung, Konfigurationsdatei und ein paar sinnvollen Tests; führe verfügbare Tests aus.

## Architekturentscheidung

Bevor du OpenClaw, Hermes oder Pi installierst: Beurteile, ob ein kleiner Python-Loop genügt. Verwende einen Agent-Harness nur, wenn er gegenüber direkter Vision+Code+TTS-Schleife konkret Mehrwert bringt. Bevorzuge eine robuste Lösung, die in wenigen Minuten einsatzbereit ist.

## Ablauf

- Repository und Umgebung prüfen.
- MVP implementieren.
- Den ersten echten 3×3-Lernzyklus demonstrieren und damit testen, ob der Tutor über meinen Code sprechen kann.
- Report: Was funktioniert tatsächlich, welche Freigaben/Interaktionen fehlen, was ist noch nicht zuverlässig?

**Wichtig:** Du bist ein Coding Agent, aber dein Endprodukt ist ein Tutor, der mein eigenes Denken schärft, kein Bot, der das Spiel für mich löst.
