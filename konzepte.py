"""Konzeptkarte (offen / mit Hilfe / kann ich) und tägliche Übungsserie.

konzepte.md ist die Wahrheit und für den Lernenden editierbar: Was er dort einträgt, gilt.
Der Coach darf nur Konzepte aus CONCEPTS einstufen und nur aufsteigen.
Unabhängig vom Spiel – später auch für Code aus Zed nutzbar.
"""
import json
import re
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAP = HERE / "konzepte.md"
PRACTICE = HERE / "uebung.json"
LEVELS = ("offen", "mit Hilfe", "kann ich")
DAILY_GOAL_MIN = 25

# id, Name, Erkennung im Code (Regex; None = nur durch Erklären/Antworten belegbar)
CONCEPTS = (
    ("variable", "Variable und Zuweisung", r"^\s*\w+\s*=[^=]"),
    ("vergleich", "Vergleich (==, !=, <, >)", r"==|!=|<=|>=|[^<>=!]<[^<=]|[^<>=-]>[^>=]"),
    ("zuweisung_vs_vergleich", "Zuweisung = gegen Vergleich ==", None),
    ("if_else", "Bedingung if / elif / else", r"^\s*(if|elif|else)\b"),
    ("while", "while-Schleife", r"^\s*while\b"),
    ("for_range", "for-Schleife mit range", r"^\s*for\s+\w+\s+in\s+range\("),
    ("verschachtelte_schleifen", "Verschachtelte Schleifen", None),  # per Einrückung erkannt
    ("funktion_def", "Eigene Funktion mit def", r"^\s*def\s+\w+\s*\("),
    ("parameter", "Parameter einer Funktion", r"^\s*def\s+\w+\s*\(\s*\w+"),
    ("rueckgabewert", "Rückgabewert mit return", r"^\s*return\b"),
    ("aufruf_klammern", "Funktion aufrufen mit Klammern", None),
    ("bool", "Wahrheitswerte True / False", r"\b(True|False)\b"),
    ("modulo", "Rest mit %", r"\w\s*%\s*\d"),
    ("and_or_not", "Logik and / or / not", r"\b(and|or|not)\b"),
    ("zaehler", "Zähler und += ", r"\+=|-="),
    ("liste", "Liste []", r"=\s*\[|\[\s*\]"),
    ("tupel", "Tupel (x, y)", r"\(\s*\w+\s*,\s*\w+\s*\)"),
    ("index", "Index liste[i]", r"\w\s*\[\s*[\w\-]+\s*\]"),
    ("append", "Liste erweitern mit append", r"\.append\("),
    ("len", "Länge mit len", r"\blen\("),
    ("global", "Geltungsbereich und global", r"^\s*global\b"),
    ("import", "Andere Datei importieren", r"^\s*import\b"),
    ("position", "Position der Drohne (get_pos_x/y)", r"get_pos_[xy]\(\)"),
    ("print_debug", "Ausgeben zum Prüfen (print)", r"\bprint\("),
)
IDS = [c[0] for c in CONCEPTS]
NAMES = {c[0]: c[1] for c in CONCEPTS}


def detect(code_by_file):
    """Welche Konzepte stehen in welchen Dateien? (benutzt != verstanden)"""
    found = {}
    for name, src in code_by_file.items():
        for cid, _, rx in CONCEPTS:
            if rx and re.search(rx, src, re.M):
                found.setdefault(cid, set()).add(name)
        if _nested_loop(src):
            found.setdefault("verschachtelte_schleifen", set()).add(name)
    return {k: sorted(v) for k, v in found.items()}


def _nested_loop(src):
    stack = []
    for line in src.splitlines():
        if not line.strip():
            continue
        ind = len(line) - len(line.lstrip("\t "))
        stack = [i for i in stack if i < ind]
        if re.match(r"\s*(for|while)\b", line):
            if stack:
                return True
            stack.append(ind)
    return False


# ---------- Karte lesen / schreiben (Markdown-Tabelle) ----------
def load_map():
    rows = {cid: {"stufe": "offen", "beleg": "", "seit": ""} for cid in IDS}
    if not MAP.exists():
        return rows
    for line in MAP.read_text().splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 4:
            continue
        cid = cells[0].strip("`")
        if cid in rows and cells[2] in LEVELS:
            rows[cid] = {"stufe": cells[2], "beleg": cells[3], "seit": cells[4] if len(cells) > 4 else ""}
    return rows


def save_map(rows, practice=None):
    p = practice if practice is not None else load_practice()
    lines = ["# Konzeptkarte", "",
             "Drei Stufen: **offen** (noch erklären) · **mit Hilfe** (kurz erinnern) · **kann ich** (nicht mehr erklären).",
             "Du darfst die Spalte *Stufe* selbst ändern – dein Eintrag gilt. Der Coach stuft nur hoch, nie runter.", "",
             "**Übungsserie:** %s" % streak_text(p), "",
             "| Konzept | Name | Stufe | Beleg | Seit |", "|---|---|---|---|---|"]
    for cid in IDS:
        r = rows[cid]
        lines.append("| `%s` | %s | %s | %s | %s |" % (cid, NAMES[cid], r["stufe"], r["beleg"].replace("|", "/"), r["seit"]))
    MAP.write_text("\n".join(lines) + "\n")


def apply_notes(notes, today=None):
    """Lernstand-Zeilen vom Coach ('mit Hilfe: rueckgabewert') übernehmen: nur bekannte IDs, nur aufsteigend."""
    today = today or time.strftime("%Y-%m-%d")
    rows = load_map()
    alias = {"erklärt": "offen", "behandelt": "offen", "selbstständig": "kann ich", "gezeigt": "kann ich"}
    changed = []
    for n in notes:
        m = re.match(r"^\s*(offen|mit Hilfe|kann ich|erklärt|behandelt|selbstständig|gezeigt)\s*:\s*`?([\w]+)`?\s*(?:[–-]\s*(.*))?$", n)
        if not m:
            continue
        lvl, cid, why = alias.get(m.group(1), m.group(1)), m.group(2), (m.group(3) or "").strip()
        if cid not in rows or LEVELS.index(lvl) <= LEVELS.index(rows[cid]["stufe"]):
            continue
        rows[cid] = {"stufe": lvl, "beleg": (why or "vom Coach")[:120], "seit": today}
        changed.append((cid, lvl))
    if changed:
        save_map(rows)
    return changed


def summary(rows=None):
    """Kompakte Zeile für jede Beobachtung an das Modell."""
    rows = rows or load_map()
    by = {lvl: [cid for cid in IDS if rows[cid]["stufe"] == lvl] for lvl in LEVELS}
    return ("KONZEPTKARTE – kann ich (NICHT erklären, höchstens beim Namen nennen): %s | mit Hilfe (kurz erinnern): %s | "
            "offen (erklären, wenn es gebraucht wird): %s" % tuple(", ".join(by[l]) or "–" for l in reversed(LEVELS)))


# ---------- Übungsserie ----------
def load_practice():
    try:
        return json.loads(PRACTICE.read_text())
    except Exception:
        return {"tage": {}}


def record_activity(minute_key=None):
    """Eine aktive Minute (Code geändert) für heute zählen. Gibt True zurück, wenn neu gezählt."""
    p = load_practice()
    now = time.localtime()
    day, minute = time.strftime("%Y-%m-%d", now), minute_key or time.strftime("%H:%M", now)
    d = p["tage"].setdefault(day, {"minuten": 0, "zuletzt": ""})
    if d.get("zuletzt") == minute:
        return False
    d["minuten"] = int(d.get("minuten", 0)) + 1
    d["zuletzt"] = minute
    PRACTICE.write_text(json.dumps(p, ensure_ascii=False, indent=1) + "\n")
    return True


def streak(p=None, today=None):
    """Aufeinanderfolgende Tage mit >= 25 aktiven Minuten. Heute zählt, sobald erreicht;
    ist heute noch nicht erreicht, ist die Serie nicht gebrochen und wird ab gestern gezählt."""
    import datetime
    p = p or load_practice()
    day = datetime.date.fromisoformat(today) if today else datetime.date.today()

    def mins(d):
        return int(p["tage"].get(d.isoformat(), {}).get("minuten", 0))

    if mins(day) < DAILY_GOAL_MIN:
        day -= datetime.timedelta(days=1)
    n = 0
    while mins(day) >= DAILY_GOAL_MIN:
        n += 1
        day -= datetime.timedelta(days=1)
    return n


def today_minutes(p=None):
    p = p or load_practice()
    return int(p["tage"].get(time.strftime("%Y-%m-%d"), {}).get("minuten", 0))


def streak_text(p=None):
    p = p or load_practice()
    return "%d Tag(e) in Folge mit mindestens %d Minuten · heute %d Minuten" % (streak(p), DAILY_GOAL_MIN, today_minutes(p))


def intro_line():
    p = load_practice()
    s, m = streak(p), today_minutes(p)
    if m >= DAILY_GOAL_MIN:
        return "Deine Serie steht bei %d Tagen, die 25 Minuten für heute hast du schon." % s
    return "Deine Serie steht bei %d Tagen. Heute fehlen noch %d Minuten." % (s, DAILY_GOAL_MIN - m)
