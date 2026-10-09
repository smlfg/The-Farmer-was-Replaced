#!/usr/bin/python3
"""TFWR-Tutor: Prozesswächter + Pi (RPC) + macOS say.

Befehle: run | status | pause | resume | now | antwort | unlocked | still | install | uninstall | log
Der LaunchAgent startet `run`. Ohne Spiel: nur pgrep alle paar Sekunden, keine Modellaufrufe.
"""
import base64, fcntl, hashlib, json, os, plistlib, re, signal, subprocess, sys, threading, time, queue
from pathlib import Path

HERE = Path(__file__).resolve().parent
STATE = Path(os.environ.get("TUTOR_STATE", Path.home() / ".tfwr-tutor"))
CFG = dict(  # alles per Umgebungsvariable TUTOR_<NAME> überschreibbar
    interval=25,          # s zwischen visuellen Beobachtungen
    debounce=4,           # s Ruhe nach Codeänderung, bevor analysiert wird (bündelt schnelles Speichern)
    think_pause=8,        # s Denkpause nach jeder Erklärung
    continue_after=8,     # s Stille nach Sprachende, dann eigener Coach-Impuls (mit ~30 s Analyse ≈ 1/min)
    max_continues=1000,   # Coach-Impulse ohne Codeänderung (praktisch unbegrenzt: 1 pro Minute)
    analysis_timeout=180,
    gap_festgefahren=45, gap_normal=60, gap_zuegig=90,  # s zwischen den Teilen CODE/LOGIK/MODELL je Modus
    ptt_key=61,           # Sprechtaste (Keycode): 61 = rechte Wahltaste (⌥) – halten zum Sprechen
    ptt_hold=0.25,        # s halten, bevor die Aufnahme startet (⌥+Taste für Sonderzeichen bleibt frei)
    mic=":0",             # ffmpeg-avfoundation-Eingang (":0" = MacBook-Mikrofon)
    whisper_model=str(Path.home() / ".local/share/whisper.cpp/ggml-small.bin"),
    speech_scale=1.0,     # Piper length-scale: >1 langsamer
    model="minimax/MiniMax-M3", thinking="low", voice="Anna", rate=175,
)
for k, v in list(CFG.items()):
    e = os.environ.get("TUTOR_" + k.upper())
    if e is not None:
        CFG[k] = type(v)(e)

GAME_PROC = "TheFarmerWasReplaced"
GAME_BIN_MARK = "TheFarmerWasReplaced.app/Contents/MacOS/TheFarmerWasReplaced"
GAME_DATA = Path.home() / "Library/Application Support/com.TheFarmerWasReplaced.TheFarmerWasReplaced"
DOCS = Path.home() / ("Library/Application Support/Steam/steamapps/common/The Farmer Was Replaced/"
                      "TheFarmerWasReplaced.app/Contents/Resources/Data/StreamingAssets/Languages/DE/docs")
PROGRESS = HERE / "progress.md"
LABEL = "com.smlfg.tfwr-tutor"
PLIST = Path.home() / "Library/LaunchAgents" / (LABEL + ".plist")
F_PAUSED, F_NOW, F_STILL, F_SAYPID = (STATE / n for n in ("paused", "now", "still", "say.pid"))
F_SCALE = STATE / "speech_scale"  # Sprechtempo (Piper length-scale), nur per Datei/Umgebung
F_DENSE = STATE / "words_per_part"  # Informationsmenge pro Nachricht: „langsamer“/„schneller“ per Sprache


def words_per_part():
    try:
        return max(20, min(80, int(F_DENSE.read_text())))
    except Exception:
        return 65


def log(msg):
    line = time.strftime("%H:%M:%S ") + msg
    print(line, flush=True)
    try:  # Loggen darf nie den Aufrufer zum Absturz bringen
        STATE.mkdir(parents=True, exist_ok=True)
        with open(STATE / "tutor.log", "a") as f:
            f.write(line + "\n")
    except OSError:
        pass


# ---------- Beobachtung (ohne Modell) ----------
def game_pid():
    r = subprocess.run(["pgrep", "-x", GAME_PROC], capture_output=True, text=True)
    for pid in r.stdout.split():
        cmd = subprocess.run(["ps", "-o", "comm=", "-p", pid], capture_output=True, text=True).stdout
        if GAME_BIN_MARK in cmd:  # das echte Spiel, nicht Steam/Overlay
            return int(pid)
    return None


def current_save():
    """Neuester Spielstand, oder None wenn Saves fehlt/leer/kein save.json."""
    saves_dir = GAME_DATA / "Saves"
    try:
        entries = list(saves_dir.iterdir())
    except OSError as e:  # Verzeichnis fehlt oder ist nicht lesbar
        log("Saves-Verzeichnis nicht lesbar (%s): %s" % (saves_dir, e))
        return None
    saves = [p for p in entries if (p / "save.json").exists()]
    if not saves:
        return None

    def mtime(p):
        try:
            return max((f.stat().st_mtime for f in p.iterdir()), default=0.0)
        except OSError as e:
            log("Spielstand nicht lesbar (%s): %s" % (p, e))
            return 0.0

    return max(saves, key=mtime)


def read_state():
    """Liest Code + Unlocks nur lesend. Rückgabe: dict mit code, unlocks, items, save."""
    s = current_save()
    if not s:
        return None
    code = {}
    for f in sorted(s.glob("*.py")):
        if f.name == "__builtins__.py":
            continue
        try:
            code[f.name] = f.read_text(errors="replace")
        except OSError as e:  # einzelne Datei überspringen, Rest weiterlesen
            log("Code-Datei nicht lesbar (%s): %s" % (f, e))
    try:
        raw = (s / "save.json").read_text()
    except OSError as e:
        log("save.json nicht lesbar (%s): %s" % (s / "save.json", e))
        return None
    try:
        d = json.loads(raw)
    except ValueError as e:
        log("save.json ungültig (%s): %s" % (s / "save.json", e))
        return None
    items, unlocks = {}, []
    if isinstance(d, dict):
        items_raw = d.get("items")
        serialize = items_raw.get("serializeList", []) if isinstance(items_raw, dict) else []
        for i in serialize:
            try:
                items[i["name"]] = i["nr"]
            except (KeyError, TypeError):
                continue
        if isinstance(d.get("unlocks"), list):
            unlocks = d["unlocks"]
    else:
        log("save.json unerwartete Struktur (%s): keine Objektwurzel" % (s / "save.json"))
    return dict(save=s.name, code=code, unlocks=unlocks, items=items)


def docs_for(unlocks):
    out = []
    names = list(unlocks) + (["expand_1"] if "move" in unlocks else [])
    for u in names:
        for f in (DOCS / "unlocks" / (u + ".md"), DOCS / "scripting" / (u + ".md")):
            if f.exists():
                out.append("### Doku %s\n%s" % (f.relative_to(DOCS), f.read_text()))
    return "\n\n".join(out)


def screenshot():
    """PNG-Bytes nur vom Spielfenster, sonst None (nie ein fremdes Fenster)."""
    helper = STATE / "winid"
    if not helper.exists():
        try:
            r = subprocess.run(["swiftc", "-O", str(HERE / "winid.swift"), "-o", str(helper)], capture_output=True)
            if r.returncode:
                log("winid-Helfer konnte nicht gebaut werden – kein Screenshot")
                return None
        except OSError as e:  # swiftc fehlt (keine Xcode-Tools)
            log("swiftc fehlt – kein Screenshot: %s" % e)
            return None
    try:
        wid = subprocess.run([str(helper)], capture_output=True, text=True).stdout.strip()
    except OSError as e:
        log("winid-Helfer nicht ausführbar – kein Screenshot: %s" % e)
        return None
    if not wid:
        return None
    raw, png = STATE / "raw.png", STATE / "shot.png"
    for f in (raw, png):  # nie ein altes Bild als aktuelles ausgeben
        f.unlink(missing_ok=True)
    try:
        if subprocess.run(["screencapture", "-x", "-o", "-l", wid, str(raw)], capture_output=True).returncode:
            return None
        subprocess.run(["sips", "-Z", "1000", str(raw), "--out", str(png)], capture_output=True)
    except OSError as e:  # screencapture/sips fehlt
        log("screencapture/sips fehlt – kein Screenshot: %s" % e)
        return None
    try:
        return png.read_bytes() if png.exists() else None
    except OSError as e:
        log("Screenshot nicht lesbar (%s): %s" % (png, e))
        return None


# ---------- Pi im RPC-Modus ----------
class Pi:
    def __init__(self):
        sp = (HERE / "prompt.md").read_text()
        sp += "\n\n# Gespeicherter Lernstand (aus früheren Sitzungen)\n" + (PROGRESS.read_text() if PROGRESS.exists() else "(leer)")
        spoken = STATE / "spoken.txt"
        if spoken.exists():
            sp += "\n\n# Zuletzt gesprochen (frühere Sitzungen)\n" + "\n".join(spoken.read_text().splitlines()[-6:])
        (STATE / "system.md").write_text(sp)
        sid = "tfwr-" + time.strftime("%Y%m%d-%H%M%S")
        self.proc = subprocess.Popen(
            ["pi", "--mode", "rpc", "--model", CFG["model"], "--thinking", CFG["thinking"],
             "--no-tools", "--no-extensions", "--no-skills", "--no-context-files", "--no-prompt-templates",
             "--offline", "--session-dir", str(STATE / "sessions"), "--session-id", sid,
             "--system-prompt", sp],
            cwd=str(STATE), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=open(STATE / "pi.err", "a"))
        self.events = queue.Queue()
        threading.Thread(target=self._reader, daemon=True).start()
        self.busy = False
        self.started = False     # agent_start für die aktuelle Anfrage gesehen
        self.settling = False    # nach abort: warten, bis der abgebrochene Lauf wirklich endet
        self.settle_t = 0.0
        self.req = 0
        log("Pi gestartet (Sitzung %s, Modell %s)" % (sid, CFG["model"]))

    def _reader(self):
        for raw in self.proc.stdout:  # JSONL, nur an \n getrennt
            try:
                self.events.put(json.loads(raw.decode().rstrip("\r\n")))
            except ValueError:
                pass
        self.events.put({"type": "_eof"})

    def send(self, cmd):
        self.proc.stdin.write((json.dumps(cmd) + "\n").encode())
        self.proc.stdin.flush()

    def ready(self):
        return not self.busy and (not self.settling or time.time() - self.settle_t > 8)

    def ask(self, text, png):
        self.req += 1
        self.started = False
        msg = {"type": "prompt", "id": "obs-%d" % self.req, "message": text}
        if png:
            msg["images"] = [{"type": "image", "data": base64.b64encode(png).decode(), "mimeType": "image/png"}]
        self.send(msg)
        self.busy = True

    def poll(self):
        """Nicht blockierend. Gibt Antworttext zurück, wenn eine Analyse fertig ist."""
        while not self.events.empty():
            e = self.events.get()
            t = e.get("type")
            if t == "_eof":
                raise RuntimeError("Pi beendet")
            if t == "response" and e.get("command") == "prompt" and not e.get("success"):
                self.busy = False
                log("Pi lehnt ab: %s" % e.get("error"))
            if t == "agent_start" and self.busy:
                self.started = True
            if t == "agent_settled":
                if self.settling:          # Ende des abgebrochenen Laufs – nicht unsere Antwort
                    self.settling = False
                    continue
                if self.busy and self.started:
                    self.busy = False
                    self.send({"type": "get_last_assistant_text", "id": "last"})
            if t == "response" and e.get("id") == "last":
                return (e.get("data") or {}).get("text") or ""
        return None

    def abort(self):
        if self.busy:
            self.send({"type": "abort"})
            self.busy = False
            self.settling = self.started   # nur ein gestarteter Lauf meldet noch ein Ende
            self.settle_t = time.time()

    def close(self):
        try:
            self.abort()
            self.proc.stdin.close()
            self.proc.wait(timeout=5)
        except Exception:
            self.proc.kill()
        log("Pi beendet")


# ---------- Sprache ----------
_voice = None      # Popen der laufenden Sprachausgabe in diesem Prozess
_say_gen = 0       # erhöht bei jedem hush(): verwirft eine gerade laufende Synthese
_last_said = {}    # text, start, dur, cut – was zuletzt tatsächlich gesprochen wurde


def speaking():
    if _voice is not None:
        return _voice.poll() is None
    try:
        os.kill(int(F_SAYPID.read_text()), 0)
        return True
    except Exception:
        return False


def hush():
    global _voice, _say_gen
    _say_gen += 1
    if _last_said and _last_said.get("cut") is None and speaking():
        _last_said["cut"] = time.time()  # Unterbrechungsstelle merken
    try:
        os.killpg(int(F_SAYPID.read_text()), signal.SIGTERM)  # ganze Gruppe: afplay/say
    except Exception:
        pass
    F_SAYPID.unlink(missing_ok=True)
    _voice = None  # sonst meldet speaking() den getöteten Prozess bis zum Reap noch als aktiv


def speech_scale():
    try:
        return float(F_SCALE.read_text())
    except Exception:
        return CFG["speech_scale"]


def say(text):
    global _voice
    hush()
    gen = _say_gen
    model = Path.home() / ".local/share/pycoach-tts/de_DE-thorsten-high.onnx"  # Standard-Stimme (vorlese)
    piper = Path.home() / ".local/bin/piper"
    if piper.exists() and model.exists():  # direkt, ohne Mesh-Ohr-Lock (flock fehlt auf macOS)
        wav = STATE / "speech.wav"
        subprocess.run([str(piper), "-m", str(model), "-c", str(model) + ".json", "-f", str(wav),
                        "--length-scale", "%.2f" % speech_scale()],
                       input=text.encode(), capture_output=True)
        if gen != _say_gen:
            return  # während der Synthese unterbrochen (Sprechtaste)
        try:
            import wave
            with wave.open(str(wav)) as w:
                dur = w.getnframes() / float(w.getframerate())
        except Exception:
            dur = len(text.split()) / 2.5
        p = subprocess.Popen(["afplay", str(wav)], start_new_session=True)
    else:
        dur = len(text.split()) / 2.5
        p = subprocess.Popen(["say", "-v", CFG["voice"], "-r", str(CFG["rate"]), text], start_new_session=True)
    _voice = p
    F_SAYPID.write_text(str(p.pid))
    _last_said.clear()
    _last_said.update(text=text, start=time.time(), dur=max(dur, 0.1), cut=None)


def said_context(now=None):
    """Was zuletzt wirklich gesprochen wurde – und wo der Lernende unterbrochen hat."""
    if not _last_said:
        return "Zuletzt gesprochen: (noch nichts in dieser Sitzung)"
    words = _last_said["text"].split()
    end = _last_said["cut"] or (now or time.time())
    frac = min(1.0, max(0.0, (end - _last_said["start"]) / _last_said["dur"]))
    if _last_said["cut"] is None or frac >= 0.98:
        return "Zuletzt vollständig gesprochen: „%s“" % _last_said["text"]
    n = int(frac * len(words))
    return ("Zuletzt gesprochen (vom Lernenden UNTERBROCHEN nach ca. %d von %d Wörtern, gehört bis „…%s“): „%s“"
            % (n, len(words), " ".join(words[max(0, n - 8):n]), _last_said["text"]))


def parse(answer):
    """Nur der Lehrtext wird gesprochen; Lernstand wird gespeichert."""
    if not answer or answer.strip().startswith("SKIP"):
        return None, []
    m = re.search(r"SPRECHEN:\s*(.*?)(?:\n\s*LERNSTAND:|$)", answer, re.S)
    text = (m.group(1) if m else "").strip()
    text = re.sub(r"[`*_#>\[\]]", "", text)
    text = re.sub(r"[\U0001F300-\U0001FAFF☀-➿]", "", text).strip()
    notes = re.findall(r"^\s*-?\s*((?:behandelt|gezeigt): .+)$", answer.split("LERNSTAND:", 1)[-1] if "LERNSTAND:" in answer else "", re.M)
    return (shorten(text) or None), notes


def _clean(text):
    text = re.sub(r"[`*_#>\[\]]", "", text)
    return re.sub(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]", "", text).strip()


LEVELS = ("CODE", "LOGIK", "MODELL")
CONTROL = ("pause", "weiter", "langsamer", "schneller")


def parse_parts(answer):
    """Antwort -> (Teile zum Sprechen, Lernstand-Notizen, Modus, Steuerung).
    Neues Format: CODE:/LOGIK:/MODELL: (je ein Teil, im Minutentakt). Alt: SPRECHEN: (ein Teil)."""
    if not answer or answer.strip().startswith("SKIP"):
        return [], [], "normal", None
    keys = LEVELS + ("SPRECHEN", "MODUS", "STEUERUNG", "LERNSTAND", "DIAGNOSE", "HILFE")
    blocks, cur = {}, None
    for line in answer.splitlines():
        m = re.match(r"^\s*(%s)\s*:\s*(.*)$" % "|".join(keys), line)
        if m:
            cur = m.group(1); blocks[cur] = m.group(2)
        elif cur:
            blocks[cur] += "\n" + line
    limit = words_per_part()
    parts = [shorten(_clean(blocks[k]), limit) for k in LEVELS if _clean(blocks.get(k, ""))]
    if not parts and _clean(blocks.get("SPRECHEN", "")):
        parts = [shorten(_clean(blocks["SPRECHEN"]), max(limit, 60))]
    modus = (blocks.get("MODUS", "normal").strip().split() or ["normal"])[0].lower()
    modus = {"zuegig": "zügig"}.get(modus, modus)
    if modus not in ("festgefahren", "normal", "zügig"):
        modus = "normal"
    ctl = (blocks.get("STEUERUNG", "").strip().split() or [""])[0].lower()
    notes = re.findall(r"^\s*-?\s*(%s: .+)$" % STATUS_RE, blocks.get("LERNSTAND", ""), re.M)
    notes = [n[0] if isinstance(n, tuple) else n for n in notes]
    diag = " ".join(blocks.get("DIAGNOSE", "").split())
    if diag:
        log("Diagnose: %s | Hilfe %s" % (diag[:160], blocks.get("HILFE", "?").strip()[:3]))
    return parts, notes, modus, (ctl if ctl in CONTROL else None)


APPROACHES = (  # Erklärwege, rotiert: Abwechslung statt immer derselben Erklärform
    "Alltagssprache: den Ablauf erst ohne Code als Handlungsanweisung beschreiben",
    "Positionen: die Drohne Schritt für Schritt mit (x, y) verfolgen",
    "Zustandstabelle: Schritt, Position, Aktion vorlesen (Schritt 1: x 0, y 0, ernten …)",
    "Pseudocode: deutsche Stichwort-Zeilen, dann Abgleich mit seinem Spielcode",
    "kleineres Beispiel: dieselbe Idee auf 2 mal 2 Feldern oder nur einer Spalte",
    "Vorhersage: er sagt voraus, was als Nächstes passiert, du löst danach auf",
    "Debugging: Erwartung gegen tatsächlichen Ablauf, erster abweichender Schritt",
    "Bild/Analogie aus dem Alltag (z. B. Rasenmähen in Bahnen, Lesen einer Buchseite)",
    "Selbst formulieren: er beschreibt einen Schritt in eigenen Worten, du fragst gezielt nach",
)


def approach_for(n):
    return APPROACHES[n % len(APPROACHES)]


def gap_for(modus):
    return CFG.get({"festgefahren": "gap_festgefahren", "zügig": "gap_zuegig"}.get(modus, "gap_normal"))


def learning_signals(history, now):
    """Lokale Lernsignale ohne Modell. history: Liste (zeit, code_text) der Codeänderungen."""
    recent = [(t, c) for t, c in history if now - t <= 300]
    wipes = 0
    for (t0, c0), (t1, c1) in zip(history, history[1:]):
        if now - t1 <= 300 and len(c0.strip()) >= 20 and len(c1.strip()) < 0.3 * len(c0.strip()):
            wipes += 1
    last = history[-1][0] if history else None
    return dict(changes_5min=len(recent), wipes_5min=wipes,
                minutes_since_change=round((now - last) / 60.0, 1) if last else None)


def shorten(text, limit=85):
    """Modelle halten die Wortgrenze nicht zuverlässig ein: ganze Sätze bis zur Grenze behalten,
    die Schlussfrage (Vorhersagefrage) immer mitnehmen."""
    if len(text.split()) <= limit:
        return text
    sents = re.split(r"(?<=[.!?])\s+", text)
    question = sents[-1] if sents[-1].endswith("?") else ""
    body = sents[:-1] if question else sents
    out, n = [], len(question.split())
    for s_ in body:
        if out and n + len(s_.split()) > limit:
            break
        out.append(s_); n += len(s_.split())
    return " ".join(out + ([question] if question else []))


def should_speak(stale, stale_drops):
    """Entscheidet, ob eine fertige Antwort gesprochen wird.

    Rückgabe: (sprechen, neuer_zähler). Eine veraltete Antwort wird nur einmal
    verworfen; ist der Zähler schon 1, wird sie trotzdem gesprochen, damit der
    Tutor bei ständigem Tippen nicht verstummt."""
    if not stale:
        return True, 0
    if stale_drops == 0:
        return False, 1
    return True, 0


STATUS_RANK = {"erklärt": 0, "behandelt": 0, "mit Hilfe": 1, "selbstständig": 2, "gezeigt": 2}
STATUS_RE = r"(erklärt|behandelt|mit Hilfe|selbstständig|gezeigt)"


def save_progress(notes):
    """Lernstand pro Konzept: erklärt -> mit Hilfe -> selbstständig. Nur aufsteigen, nie absteigen;
    exakte Duplikate ignorieren. Alte Einträge (behandelt/gezeigt) gelten als erklärt/selbstständig."""
    old = PROGRESS.read_text() if PROGRESS.exists() else "# Lernstand\n\n"
    lines = old.splitlines()
    index = {}
    for i, line in enumerate(lines):
        m = re.match(r"^\s*-\s*%s:\s*(.+?)\s*(?:\((\d{4}-\d{2}-\d{2})\))?\s*$" % STATUS_RE, line)
        if m:
            index[m.group(2).strip()] = (i, m.group(1))
    today = time.strftime("%Y-%m-%d")
    changed = False
    for n in notes:
        m = re.match(r"^\s*%s:\s*(.+?)\s*$" % STATUS_RE, n)
        if not m:
            continue
        status, concept = m.group(1), m.group(2).strip()
        if concept in index:
            i, cur = index[concept]
            if STATUS_RANK[status] > STATUS_RANK[cur]:
                lines[i] = "- %s: %s  (%s)" % (status, concept, today)
                index[concept] = (i, status)
                changed = True
        else:
            lines.append("- %s: %s  (%s)" % (status, concept, today))
            index[concept] = (len(lines) - 1, status)
            changed = True
    if changed:
        PROGRESS.write_text("\n".join(lines) + "\n")


def answer_path():
    return STATE / "answer_in.txt"


def manual_unlocks():
    p = STATE / "manual_unlocks.txt"
    if p.exists():
        return [l.strip() for l in p.read_text().splitlines() if l.strip()]
    return []


def observation(reason, st, prev, png, first, extra=None):
    parts = ["BEOBACHTUNG – Anlass: %s" % reason,
             "Screenshot: " + ("angehängt (Spielfenster)" if png else "kein Screenshot verfügbar – nichts Visuelles behaupten"),
             "Spielstand: %s" % st["save"]]
    for name, src in st["code"].items():
        changed = (not prev) or prev["code"].get(name) != src
        parts.append("### %s%s\n```\n%s\n```" % (name, " (geändert)" if changed and prev else "", src or "(leer)"))
    if first or (prev and prev["unlocks"] != st["unlocks"]):
        new = [u for u in st["unlocks"] if not prev or u not in prev["unlocks"]]
        parts.append("unlocks: " + ", ".join(st["unlocks"]))
        if prev and new:
            parts.append("NEU freigeschaltet: " + ", ".join(new))
        parts.append("# In-Game-Doku\n" + docs_for(new if (prev and new) else st["unlocks"]))
    man = manual_unlocks()
    if man:
        parts.append("vom Lernenden gemeldet, nicht belegt: " + ", ".join(man))
    parts.append("Inventar: " + ", ".join("%s=%g" % kv for kv in st["items"].items()))
    if extra:
        parts.extend(extra)
    return "\n\n".join(parts)


# ---------- Push-to-Talk ----------
HALLUCINATIONS = ("untertitel", "vielen dank fürs zuschauen", "danke fürs zuschauen", "copyright", "swr", "zdf")


def clean_transcript(text):
    """Leere/erfundene Whisper-Ausgaben verwerfen ([MUSIK], Untertitel-Floskeln …)."""
    t = re.sub(r"\[[^\]]*\]|\([^)]*\)|\*[^*]*\*", " ", text or "")
    t = re.sub(r"\s+", " ", t).strip()
    if len(re.sub(r"[^\wäöüß]", "", t.lower())) < 2:
        return None
    if any(h in t.lower() for h in HALLUCINATIONS) and len(t.split()) <= 8:
        return None
    return t


def local_intent(text):
    """Kurze Steuerbefehle ohne Modell. Rückgabe: pause|weiter|langsamer|schneller|None."""
    t = re.sub(r"[^\wäöüß ]", "", text.lower()).strip()
    if len(t.split()) > 8:
        return None
    if re.fullmatch(r"(ok |okay |ja )?(weiter|mach weiter|weiter bitte|fortsetzen|kannst weitermachen)", t):
        return "weiter"
    if re.search(r"(lass mich.*(überlegen|nachdenken|selbst)|^pause$|^stopp?$|^sei still$|^ruhe$)", t):
        return "pause"
    if re.fullmatch(r"(etwas |bitte )?langsamer( bitte)?", t):
        return "langsamer"
    if re.fullmatch(r"(etwas |bitte )?schneller( bitte)?", t):
        return "schneller"
    return None


def cue(name):
    subprocess.run(["afplay", "/System/Library/Sounds/%s.aiff" % name], capture_output=True)


class PTT:
    """Sprechtaste halten -> Aufnahme (ffmpeg) -> loslassen -> whisper-cli (lokal, deutsch).
    Mikrofon ist nur während der Aufnahme offen. Ergebnisse landen in self.results."""

    def __init__(self):
        self.results = queue.Queue()
        self.active = False      # Aufnahme oder Transkription läuft -> nichts anderes darf sprechen
        self.rec = None
        self.armed = False
        self.press = 0           # zählt Tastendrücke: nur der Timer des letzten Drucks darf starten
        self.lock = threading.Lock()
        self.helper = None
        helper = STATE / "ptt"
        src = HERE / "ptt.swift"
        if not helper.exists() or helper.stat().st_mtime < src.stat().st_mtime:
            if subprocess.run(["swiftc", "-O", str(src), "-o", str(helper)], capture_output=True).returncode:
                log("Sprechtaste: Helfer konnte nicht gebaut werden"); return
        self.helper = subprocess.Popen([str(helper), str(CFG["ptt_key"])], stdout=subprocess.PIPE, text=True)
        threading.Thread(target=self._reader, daemon=True).start()

    def _reader(self):
        for line in self.helper.stdout:
            ev = line.strip()
            if ev == "NOPERM":
                log("Sprechtaste: Eingabeüberwachung für „TFWR Tutor“ fehlt (Datenschutz & Sicherheit)")
            elif ev == "READY":
                log("Sprechtaste bereit (Keycode %s halten)" % CFG["ptt_key"])
            elif ev == "DOWN":
                self.armed = True
                self.press += 1
                threading.Timer(CFG["ptt_hold"], self._maybe_start, args=(self.press,)).start()
            elif ev == "OTHER":
                self.armed = False  # ⌥+Taste = Sonderzeichen, keine Sprechtaste
                if self.rec:
                    self._stop(discard=True)
            elif ev == "UP":
                self.armed = False
                if self.rec:
                    self._stop()

    def _maybe_start(self, press):
        with self.lock:  # nie zwei Aufnahmen gleichzeitig
            if not self.armed or self.rec or press != self.press:
                return
            self._start()

    def _start(self):
        self.active = True
        hush()                      # TTS sofort aus (nie die eigene Stimme aufnehmen)
        cue("Tink")                 # Startton VOR der Aufnahme
        wav = STATE / "mic.wav"
        wav.unlink(missing_ok=True)
        self.rec = subprocess.Popen(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "avfoundation",
                                     "-i", CFG["mic"], "-ac", "1", "-ar", "16000", "-y", str(wav)],
                                    stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        self.t0 = time.time()
        log("höre zu …")

    def _stop(self, discard=False):
        with self.lock:
            rec, self.rec = self.rec, None
        if rec is None:
            return
        try:
            rec.stdin.write(b"q"); rec.stdin.flush()  # ffmpeg sauber beenden
            rec.wait(timeout=3)
        except Exception:
            rec.kill()
        err = rec.stderr.read().decode(errors="replace") if rec.stderr else ""
        cue("Pop")                  # Endton NACH der Aufnahme
        if discard:
            log("Aufnahme verworfen (andere Taste)"); self.active = False; return
        threading.Thread(target=self._transcribe, args=(time.time() - self.t0, err), daemon=True).start()

    def _transcribe(self, secs, err):
        try:
            self._transcribe_inner(secs, err)
        finally:
            self.active = False

    def _transcribe_inner(self, secs, err):
        wav = STATE / "mic.wav"
        if not wav.exists() or wav.stat().st_size < 2000:
            log("Aufnahme leer – Mikrofon-Berechtigung? %s" % err.strip()[:120])
            self.results.put(("error", "Ich habe nichts gehört. Ist das Mikrofon für TFWR Tutor erlaubt?")); return
        if secs < 0.6:
            self.results.put(("error", None)); return  # nur angetippt
        vol = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(wav), "-af", "volumedetect", "-f", "null", "-"],
                             capture_output=True, text=True).stderr
        m = re.search(r"max_volume: (-?[\d.]+) dB", vol)
        if m and float(m.group(1)) < -45:
            self.results.put(("error", "Ich habe nichts verstanden.")); return
        r = subprocess.run(["whisper-cli", "-m", CFG["whisper_model"], "-l", "de", "-nt", "-np", "-f", str(wav)],
                           capture_output=True, text=True)
        text = clean_transcript(r.stdout)
        log("gehört: %s" % (text or "(unverständlich)"))
        self.results.put(("text", text) if text else ("error", "Ich habe nichts verstanden."))

    def close(self):
        if self.rec:
            self.rec.kill(); self.rec = None   # Mikrofon frei
        if self.helper:
            self.helper.kill()
        self.active = False


# ---------- Hauptschleife ----------
def session(gpid):
    """Eine Tutor-Sitzung, solange das Spiel läuft."""
    pi, prev, sent_hash = Pi(), None, None
    ptt = PTT()
    last_shot = last_spoke = last_start = 0.0
    pending_since = None
    continues = 0
    asked_hash = None
    stale_drops = 0
    forced = False
    answer_text = None
    voice_text = None
    voice_pending = False        # Antwort auf Spracheingabe steht aus -> nichts anderes spricht
    parts, modus = [], "normal"
    approach_n = int(time.time()) % len(APPROACHES)  # Startpunkt der Rotation variiert je Sitzung
    history, last_code = [], None
    fails = 0
    ask_t, forced_last = 0.0, False
    try:
        while game_pid() == gpid:
            time.sleep(0.5)
            now = time.time()
            # --- Spracheingabe hat Vorrang
            while not ptt.results.empty():
                kind, val = ptt.results.get()
                if kind == "error":
                    if val:
                        say(val)
                    continue
                intent = local_intent(val)
                if intent == "pause":
                    F_PAUSED.touch(); say("Okay, ich warte. Sag weiter, wenn du soweit bist.")
                elif intent == "weiter":
                    F_PAUSED.unlink(missing_ok=True); say("Okay, weiter."); continues = 0
                    last_spoke = 0.0
                elif intent in ("langsamer", "schneller"):
                    w = words_per_part() + (-20 if intent == "langsamer" else 20)
                    F_DENSE.write_text(str(max(20, min(80, w))))
                    say("Okay, ab jetzt kleinere Häppchen." if intent == "langsamer" else "Okay, ab jetzt mehr auf einmal.")
                else:
                    voice_text = val
                log("Sprachbefehl: %s" % (intent or "Frage an Tutor"))
            if ptt.active:  # Aufnahme/Transkription läuft: niemand sonst spricht oder analysiert
                if pi.busy and not voice_pending:
                    pi.abort()
                parts = []
                continue
            if F_STILL.exists():
                F_STILL.unlink(); hush(); pi.abort(); parts = []
            if F_NOW.exists():
                F_NOW.unlink(); hush(); pi.abort(); parts = []; forced = True
            if answer_path().exists():
                txt = answer_path().read_text().strip()
                answer_path().unlink(missing_ok=True)
                if txt:
                    hush(); pi.abort(); parts = []; answer_text = txt
            if voice_text is not None and not voice_pending:
                hush(); pi.abort(); parts = []
            paused = F_PAUSED.exists()
            if paused and not forced and answer_text is None and voice_text is None and not voice_pending:
                parts = []
                continue
            try:
                ans = pi.poll()
            except RuntimeError:
                fails += 1
                log("Pi abgestürzt (%d)" % fails)
                if fails >= 3:
                    log("zu viele Fehler – Tutor ruht bis zum nächsten Spielstart"); return
                pi = Pi(); prev = None; voice_pending = False; continue
            st = read_state()
            if not st:
                continue
            code_now = "\n".join(st["code"].values())
            if code_now != last_code:
                history = [(t, c) for t, c in history if now - t <= 600] + [(now, code_now)]
                last_code = code_now
            h = hashlib.md5(json.dumps([st["code"], st["unlocks"], manual_unlocks()], sort_keys=True).encode()).hexdigest()  # Inventar zählt nicht
            if ans is not None:
                stale = h != asked_hash and not forced_last
                speak, stale_drops = should_speak(stale, stale_drops)
                if not speak:
                    log("veraltet verworfen – Stand hat sich geändert")
                else:
                    if stale:
                        log("leicht veraltet, trotzdem gesprochen")
                    new_parts, notes, modus, ctl = parse_parts(ans)
                    save_progress(notes)
                    if ctl == "pause":
                        F_PAUSED.touch()
                    elif ctl == "weiter":
                        F_PAUSED.unlink(missing_ok=True)
                    if new_parts:
                        parts = new_parts
                        log("Modus: %s, %d Teil(e)" % (modus, len(parts)))
                    else:
                        log("SKIP")
                    last_spoke = time.time()
                voice_pending = False
                fails = 0
            # nächster Teil (CODE -> LOGIK -> MODELL) ohne Modellaufruf
            if parts and not speaking() and not pi.busy and \
                    (last_start == 0 or now - last_start >= gap_for(modus) or forced_last):
                text = parts.pop(0)
                forced_last = False
                with open(STATE / "spoken.txt", "a") as f:
                    f.write("[%s] %s\n" % (time.strftime("%H:%M"), text))
                log("spricht: %s…" % text[:90])
                say(text)
                last_start = last_spoke = time.time()
                continue
            if pi.busy:
                if now - ask_t > CFG["analysis_timeout"]:
                    log("Analyse-Timeout"); pi.abort(); voice_pending = False
                continue
            if not pi.ready():
                continue
            if speaking():
                last_spoke = now
                continue
            # Anlass bestimmen
            reason = None
            if voice_text is not None:
                reason = "DER LERNENDE SAGT (gesprochen): „%s“" % voice_text
            elif answer_text is not None:
                reason = "ANTWORT DES LERNENDEN: %s" % answer_text
            elif forced:
                reason = "jetzt erklären (vom Lernenden angefordert, nicht SKIP)"
            elif parts:
                continue  # erst die vorhandenen Teile sprechen
            elif paused:
                continue
            elif h != sent_hash:
                pending_since = pending_since or now
                if now - pending_since >= CFG["debounce"] and now - last_spoke >= CFG["think_pause"]:
                    reason = "Code/Spielstand geändert"
            elif now - last_shot >= CFG["interval"] and now - last_start >= gap_for(modus) \
                    and now - last_spoke >= CFG["continue_after"] and continues < CFG["max_continues"]:
                reason = "weiter (Coach-Impuls fällig: nicht SKIP, nichts wiederholen)"
                continues += 1
            if not reason:
                continue
            if not reason.startswith("weiter"):
                continues = 0
            png = screenshot()
            last_shot = now
            extra = [said_context(now),
                     "Lernsignale: " + json.dumps(learning_signals(history, now), ensure_ascii=False),
                     "Gewünschte Länge: höchstens %d Wörter pro Teil, ein kleiner Gedanke pro Teil." % words_per_part(),
                     "Vorgeschlagener Erklärweg diesmal: %s." % approach_for(approach_n)]
            approach_n += 1
            pi.ask(observation(reason, st, prev, png, prev is None, extra), png)
            log("analysiere: %s%s" % (reason[:80], "" if png else " (ohne Bild)"))
            urgent = forced or answer_text is not None or voice_text is not None
            voice_pending = voice_text is not None
            ask_t, asked_hash, forced_last = now, h, urgent
            prev, sent_hash, pending_since, forced, answer_text, voice_text = st, h, None, False, None, None
    finally:
        ptt.close()   # Mikrofon frei, Sprechtaste aus
        hush()
        pi.close()


def run():
    STATE.mkdir(parents=True, exist_ok=True)
    lock = open(STATE / "lock", "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("läuft bereits"); return
    signal.signal(signal.SIGTERM, lambda *a: sys.exit(0))
    log("Wächter aktiv")
    try:
        while True:
            gpid = game_pid()
            if gpid:
                log("Spiel erkannt (pid %d)" % gpid)
                session(gpid)
                log("Spiel beendet – Bild und Sprache gestoppt, Lernstand gespeichert")
            time.sleep(3)
    finally:
        hush()


APP = Path.home() / "Applications/TFWR Tutor.app"
APP_EXE = APP / "Contents/MacOS/tfwr-tutor"


def build_app():
    """Starter-App mit eigener Identität für die Bildschirmaufnahme-Freigabe. Nur bauen, wenn sie fehlt:
    jeder Neubau ändert die Signatur, und macOS vergisst dann die Freigabe."""
    info = APP / "Contents/Info.plist"
    if APP_EXE.exists() and info.exists() and b"NSMicrophoneUsageDescription" in info.read_bytes():
        return
    APP_EXE.parent.mkdir(parents=True, exist_ok=True)
    plistlib.dump(dict(CFBundleIdentifier=LABEL, CFBundleName="TFWR Tutor", CFBundleExecutable="tfwr-tutor",
                       CFBundlePackageType="APPL", CFBundleVersion="2", LSUIElement=True,
                       NSMicrophoneUsageDescription="Sprechtaste: Deine Frage an den Tutor aufnehmen (nur solange die Taste gehalten wird)."),
                  (APP / "Contents/Info.plist").open("wb"))
    subprocess.run(["swiftc", "-O", str(HERE / "launcher.swift"), "-o", str(APP_EXE)], check=True)
    subprocess.run(["codesign", "--force", "-s", "-", "--identifier", LABEL, str(APP)], check=True)
    print("Starter-App gebaut:", APP)


def install():
    build_app()
    PLIST.parent.mkdir(parents=True, exist_ok=True)
    env = {"PATH": "%s/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin" % Path.home()}
    plistlib.dump(dict(Label=LABEL, ProgramArguments=[str(APP_EXE), str(HERE / "tutor.py")],
                       RunAtLoad=True, KeepAlive=dict(SuccessfulExit=False), ThrottleInterval=60,
                       EnvironmentVariables=env, ProcessType="Interactive",
                       StandardOutPath=str(STATE / "launchd.log"), StandardErrorPath=str(STATE / "launchd.log")),
                  PLIST.open("wb"))
    uid = os.getuid()
    subprocess.run(["launchctl", "bootout", "gui/%d/%s" % (uid, LABEL)], capture_output=True)
    for _ in range(10):  # bootout ist asynchron; bootstrap direkt danach scheitert sonst mit Fehler 5
        if subprocess.run(["launchctl", "bootstrap", "gui/%d" % uid, str(PLIST)], capture_output=True).returncode == 0:
            break
        time.sleep(1)
    else:
        sys.exit("launchctl bootstrap fehlgeschlagen")
    print("Autostart aktiv:", PLIST)
    print("Bildschirmaufnahme einmalig erlauben für:", APP)


def uninstall():
    subprocess.run(["launchctl", "bootout", "gui/%d/%s" % (os.getuid(), LABEL)], capture_output=True)
    PLIST.unlink(missing_ok=True)
    hush()
    print("Autostart deaktiviert, Tutor gestoppt")


def status():
    r = subprocess.run(["launchctl", "print", "gui/%d/%s" % (os.getuid(), LABEL)], capture_output=True, text=True)
    print("Autostart:", "aktiv" if r.returncode == 0 else "aus")
    print("Spiel:", "läuft" if game_pid() else "aus", "| Pause:", "ja" if F_PAUSED.exists() else "nein",
          "| spricht:", "ja" if speaking() else "nein")
    if (STATE / "tutor.log").exists():
        print("".join((STATE / "tutor.log").read_text().splitlines(True)[-4:]), end="")


def cmd_answer(text):
    text = (text or "").strip()
    if not text:
        print("Nutzung: python3 tutor.py antwort \"<text>\"")
        return
    answer_path().write_text(text + "\n")
    print("Antwort aufgenommen – der Tutor geht gleich darauf ein.")


def cmd_unlock(name):
    name = (name or "").strip()
    if not name:
        print("Nutzung: python3 tutor.py unlocked \"<X>\"")
        return
    with open(STATE / "manual_unlocks.txt", "a") as f:
        f.write(name + "\n")
    print("Freischaltung notiert (vom Lernenden gemeldet, nicht belegt): %s" % name)


if __name__ == "__main__":
    STATE.mkdir(parents=True, exist_ok=True)
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "run": run()
    elif cmd == "install": install()
    elif cmd == "uninstall": uninstall()
    elif cmd == "status": status()
    elif cmd == "pause": F_PAUSED.touch(); hush(); print("pausiert (bleibt, bis du resume sagst)")
    elif cmd == "resume": F_PAUSED.unlink(missing_ok=True); print("weiter")
    elif cmd == "now": hush(); F_NOW.touch(); print("erkläre gleich")
    elif cmd == "antwort": cmd_answer(sys.argv[2] if len(sys.argv) > 2 else "")
    elif cmd == "unlocked": cmd_unlock(sys.argv[2] if len(sys.argv) > 2 else "")
    elif cmd == "still": F_STILL.touch(); hush(); print("still")
    elif cmd == "log": os.execvp("tail", ["tail", "-f", str(STATE / "tutor.log")])
    else: print(__doc__)
