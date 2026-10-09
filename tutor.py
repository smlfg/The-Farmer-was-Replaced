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
    think_pause=20,       # s Denkpause nach jeder Erklärung
    continue_after=90,    # s Stille, nach denen der Tutor von sich aus fortsetzt
    max_continues=2,      # höchstens so oft ohne neue Änderung fortsetzen
    analysis_timeout=120,
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
        subprocess.run(["sips", "-Z", "1400", str(raw), "--out", str(png)], capture_output=True)
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

    def ask(self, text, png):
        msg = {"type": "prompt", "id": "obs", "message": text}
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
            if t == "agent_settled" and self.busy:
                self.busy = False
                self.send({"type": "get_last_assistant_text", "id": "last"})
            if t == "response" and e.get("id") == "last":
                return (e.get("data") or {}).get("text") or ""
        return None

    def abort(self):
        if self.busy:
            self.send({"type": "abort"})
            self.busy = False

    def close(self):
        try:
            self.abort()
            self.proc.stdin.close()
            self.proc.wait(timeout=5)
        except Exception:
            self.proc.kill()
        log("Pi beendet")


# ---------- Sprache ----------
_voice = None  # Popen der laufenden Sprachausgabe in diesem Prozess


def speaking():
    if _voice is not None:
        return _voice.poll() is None
    try:
        os.kill(int(F_SAYPID.read_text()), 0)
        return True
    except Exception:
        return False


def hush():
    global _voice
    try:
        os.killpg(int(F_SAYPID.read_text()), signal.SIGTERM)  # ganze Gruppe: piper + afplay
    except Exception:
        pass
    F_SAYPID.unlink(missing_ok=True)
    _voice = None  # sonst meldet speaking() den getöteten Prozess bis zum Reap noch als aktiv


def say(text):
    global _voice
    hush()
    model = Path.home() / ".local/share/pycoach-tts/de_DE-thorsten-high.onnx"  # Standard-Stimme (vorlese)
    piper = Path.home() / ".local/bin/piper"
    if piper.exists() and model.exists():  # direkt, ohne Mesh-Ohr-Lock (flock fehlt auf macOS)
        wav = STATE / "speech.wav"
        sh = '"$0" -m "$1" -c "$1.json" -f "$2" >/dev/null 2>&1 && exec afplay "$2"'
        p = subprocess.Popen(["/bin/sh", "-c", sh, str(piper), str(model), str(wav)],
                             stdin=subprocess.PIPE, start_new_session=True)
        p.stdin.write(text.encode()); p.stdin.close()
    else:
        p = subprocess.Popen(["say", "-v", CFG["voice"], "-r", str(CFG["rate"]), text], start_new_session=True)
    _voice = p
    F_SAYPID.write_text(str(p.pid))


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


def save_progress(notes):
    """Hängt Lernstand-Zeilen an. Exakte Duplikate werden ignoriert; „gezeigt“ ersetzt
    ein vorhandenes „behandelt“ desselben Konzepts, aber nie umgekehrt."""
    old = PROGRESS.read_text() if PROGRESS.exists() else "# Lernstand\n\n"
    lines = old.splitlines()
    index = {}
    for i, line in enumerate(lines):
        m = re.match(r"^\s*-\s*(behandelt|gezeigt):\s*(.+?)\s*(?:\((\d{4}-\d{2}-\d{2})\))?\s*$", line)
        if m:
            index[m.group(2).strip()] = i
    today = time.strftime("%Y-%m-%d")
    changed = False
    for n in notes:
        m = re.match(r"^\s*(behandelt|gezeigt):\s*(.+?)\s*$", n)
        if not m:
            continue
        status, concept = m.group(1), m.group(2).strip()
        if concept in index:
            i = index[concept]
            if status == "gezeigt" and lines[i].lstrip().startswith("- behandelt:"):
                lines[i] = "- gezeigt: %s  (%s)" % (concept, today)
                changed = True
        else:
            lines.append("- %s: %s  (%s)" % (status, concept, today))
            index[concept] = len(lines) - 1
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


def observation(reason, st, prev, png, first):
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
    return "\n\n".join(parts)


# ---------- Hauptschleife ----------
def session(gpid):
    """Eine Tutor-Sitzung, solange das Spiel läuft."""
    pi, prev, sent_hash = Pi(), None, None
    last_shot = last_spoke = 0.0
    pending_since = None
    continues = 0
    asked_hash = None
    forced = False
    answer_text = None
    fails = 0
    ask_t, forced_last = 0.0, False
    try:
        while game_pid() == gpid:
            time.sleep(1)
            now = time.time()
            if F_STILL.exists():
                F_STILL.unlink(); hush(); pi.abort()
            if F_NOW.exists():
                F_NOW.unlink(); hush(); pi.abort(); forced = True
            if answer_path().exists():
                txt = answer_path().read_text().strip()
                answer_path().unlink(missing_ok=True)
                if txt:
                    hush(); pi.abort(); answer_text = txt
            paused = F_PAUSED.exists()
            if paused and not forced and answer_text is None:
                if speaking(): hush()
                continue
            try:
                ans = pi.poll()
            except RuntimeError:
                fails += 1
                log("Pi abgestürzt (%d)" % fails)
                if fails >= 3:
                    log("zu viele Fehler – Tutor ruht bis zum nächsten Spielstart"); return
                pi = Pi(); prev = None; continue
            st = read_state()
            if not st:
                continue
            h = hashlib.md5(json.dumps([st["code"], st["unlocks"], manual_unlocks()], sort_keys=True).encode()).hexdigest()  # Inventar zählt nicht
            if ans is not None:
                if h != asked_hash and not forced_last:
                    log("veraltet verworfen – Stand hat sich geändert")
                else:
                    text, notes = parse(ans)
                    save_progress(notes)
                    if text:
                        with open(STATE / "spoken.txt", "a") as f:
                            f.write("[%s] %s\n" % (time.strftime("%H:%M"), text))
                        log("spricht: %s…" % text[:90])
                        say(text)
                    else:
                        log("SKIP")
                    last_spoke = time.time()
                fails = 0
            if pi.busy:
                if now - ask_t > CFG["analysis_timeout"]:
                    log("Analyse-Timeout"); pi.abort()
                continue
            if speaking():
                last_spoke = now
                continue
            # Anlass bestimmen
            reason = None
            if answer_text is not None:
                reason = "ANTWORT DES LERNENDEN: %s" % answer_text
            elif forced:
                reason = "jetzt erklären (vom Lernenden angefordert, nicht SKIP)"
            elif h != sent_hash:
                pending_since = pending_since or now
                if now - pending_since >= CFG["debounce"] and now - last_spoke >= CFG["think_pause"]:
                    reason = "Code/Spielstand geändert"
            elif now - last_shot >= CFG["interval"] and now - last_spoke >= CFG["continue_after"] \
                    and continues < CFG["max_continues"]:
                reason = "weiter"; continues += 1
            if not reason:
                continue
            if reason != "weiter":
                continues = 0
            png = screenshot()
            last_shot = now
            pi.ask(observation(reason, st, prev, png, prev is None), png)
            log("analysiere: %s%s" % (reason, "" if png else " (ohne Bild)"))
            ask_t, asked_hash, forced_last = now, h, (forced or answer_text is not None)
            prev, sent_hash, pending_since, forced, answer_text = st, h, None, False, None
    finally:
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
    if APP_EXE.exists():
        return
    APP_EXE.parent.mkdir(parents=True, exist_ok=True)
    plistlib.dump(dict(CFBundleIdentifier=LABEL, CFBundleName="TFWR Tutor", CFBundleExecutable="tfwr-tutor",
                       CFBundlePackageType="APPL", CFBundleVersion="1", LSUIElement=True),
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
