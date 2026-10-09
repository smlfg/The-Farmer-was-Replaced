# Lokal vs. Cloud (gemessen 2026-10-09)

Gleicher Prompt (`prompt.md`), echte Beobachtung aus dem Spielstand „Programmieren lernen“, ein Bild, Pi im RPC-Modus ohne Werkzeuge.

| Modell | Zeit bis Antwort | gesprochene Wörter | Format |
|---|---|---|---|
| `ollama/muse-glimmer:30b-mlx` (lokal, M3 Max) | 362 s | 357 | gebrochen: Markdown, Codeblöcke, kein `SPRECHEN:` |
| `minimax/MiniMax-M3` (Cloud) | 28 s | 105 | ok (Länge wird in `shorten()` gekappt) |

Ergebnis: Lokal ist mit diesem Modell für Echtzeit-Tutoring nicht brauchbar. Default bleibt MiniMax-M3;
Screenshots, Spielcode und Lernstand gehen dabei an MiniMax. Umschalten: `TUTOR_MODEL` in den
`EnvironmentVariables` des LaunchAgents setzen.
