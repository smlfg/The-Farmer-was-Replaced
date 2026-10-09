"""Small local learning companion used when Pi/API cannot answer.

Tries a loopback Ollama model, then a deterministic one-step hint. No cloud
calls, no screenshot upload, no game-code modifications. Shares Pi's interface.
"""
import hashlib
import json
import queue
import re
import threading
import urllib.request

CODE_BLOCK = re.compile(r"^### ([^\n]+?)\n```\n(.*?)\n```", re.M | re.S)


def focus_from_observation(observation):
    """Choose the recently edited file, rather than assuming main.py."""
    files = []
    for heading, code in CODE_BLOCK.findall(observation):
        changed = heading.endswith(" (geändert)")
        name = heading.removesuffix(" (geändert)")
        files.append((name, code, changed))
    marker = re.search(r"^Fokusdatei \(jüngste Änderung\): (.+)$", observation, re.M)
    preferred = marker.group(1).strip() if marker else ""
    choice = next((f for f in files if f[0] == preferred), None)
    if choice is None:
        choice = next((f for f in reversed(files) if f[2]), None)
    if choice is None:
        choice = next((f for f in files if f[0] == "main.py" and f[1].strip() not in ("", "(leer)")), None)
    if choice is None:
        choice = next((f for f in files if f[1].strip() not in ("", "(leer)")), None)
    return choice[:2] if choice else ("", "")


def context_from_observation(observation):
    filename, code = focus_from_observation(observation)
    goal = re.search(r"Tutor-Notizbuch .*?Ziel: ([^;\n]+)", observation)
    voice = re.search(r"DER LERNENDE SAGT \(gesprochen\): [„“\"](.+?)[“”\"]", observation)
    answer = re.search(r"ANTWORT DES LERNENDEN: ([^\n]+)", observation)
    reason = observation.split("\n", 1)[0]
    error = re.search(r"FEHLER BEIM AUSFÜHREN[^\n]*\n([^\n]+)", observation)
    return {"file": filename, "code": code[:7000],
            "goal": goal.group(1).strip() if goal else "",
            "user": (voice.group(1) if voice else answer.group(1) if answer else ""),
            "reason": reason, "error": error.group(1)[:600] if error else ""}


def simple_hint(ctx):
    """Offline baseline: one real concept and one question, no invented game state."""
    error = ctx.get("error", "").lower()
    if error:
        if "bevor ihr ein wert" in error or "unboundlocal" in error or "before assignment" in error:
            return ("Diese Fehlermeldung betrifft den Geltungsbereich einer Variablen. "
                    "Innerhalb der Funktion wird sie als lokal behandelt, aber vor dem Lesen "
                    "noch nicht mit einem Wert belegt. Wo wird der Wert in deiner Funktion zuerst gesetzt?")
        if "nonetype" in error or "none" in error:
            return ("Eine Funktion ohne Rückgabewert liefert None. "
                    "Prüfe, welcher Pfad deiner Funktion ohne einen Wert endet. "
                    "Was wird genau in diesem Fall zurückgegeben?")
        return ("Der Laufzeitfehler ist ein konkreter Hinweis auf den ersten fehlschlagenden Schritt. "
                "Lies die genannte Zeile und überprüfe die Werte direkt davor. "
                "Welche Annahme dieser Zeile könnte falsch sein?")
    c = ctx["code"].lower()
    u = ctx["user"].lower()
    if "checklist" in c or ("koordinate" in u and "liste" in u):
        return ("Trenne zwei Entscheidungen: Welches Tupel aus der Liste ist dein Ziel? "
                "Und welcher Wert darin ist x oder y? Vergleiche danach nur eine Achse mit deiner "
                "aktuellen Position. Welche Richtung verkleinert den Abstand auf der x-Achse?")
    if "get_pos_x" in c or "get_pos_y" in c or "navigation" in u:
        return ("Navigation heißt: aktuelle Position mit Zielposition vergleichen und einen Schritt "
                "in Richtung des Ziels ausführen. Wiederhole das, bis beide Koordinaten übereinstimmen. "
                "Was muss bei der x-Koordinate gelten, damit du aufhörst nach Osten zu gehen?")
    if "full" in c or "fieldok" in c or "fielddo" in c:
        return ("Unterscheide den Zustand eines Felds vom Zustand des ganzen Quadrats. "
                "Ein Feld kann bereit sein, obwohl ein anderes noch wächst. "
                "Was musst du nach jeder vollständigen Kontrollrunde über alle Felder wissen?")
    if "dead_pumpkin" in c or "pumpkin" in c:
        return ("Ein neu gepflanzter Kürbis ist nicht sofort erntereif. "
                "Unterscheide daher repariert, wachsend und fertig. "
                "Welche Aussage muss über alle Felder gelten, bevor du den großen Kürbis erntest?")
    if "for " in c or "while " in c or "move(" in c:
        return ("Trenne zwei Teilaufgaben: ein Feld bearbeiten und zum nächsten Feld gelangen. "
                "Teste zuerst, ob dein Bewegungsmuster jedes Feld genau einmal besucht. "
                "Wo steht die Drohne nach einer vollständigen Reihe?")
    if ctx["user"]:
        return ("Ich kann ohne lokales Sprachmodell nur einen kleinen Schritt begleiten. "
                "Beschreibe bitte das gewünschte Ergebnis an einem einzigen konkreten Feld: "
                "Was soll sich nach dem nächsten Befehl geändert haben?")
    return ("Arbeite zuerst am Ablauf in Worten, noch ohne Python. "
            "Was ist der Zustand vor deinem nächsten Schritt, was soll danach anders sein, "
            "und woran kannst du das überprüfen?")


def local_model_reply(ctx, model, url, timeout):
    """Only connects to a loopback Ollama endpoint, never an external host."""
    from urllib.parse import urlsplit
    host = urlsplit(url).hostname
    if host not in ("127.0.0.1", "localhost", "::1"):
        raise ValueError("Local model URL must point to loopback")
    prompt = (
        "Du bist ein ruhiger, gesprochener Python-Tutor beim Spiel The Farmer Was Replaced. "
        "Das Ziel ist selbststaendiges algorithmisches Denken. Verwende nur den folgenden Code, "
        "die Frage und das angegebene Ziel als Belege. Stelle keine Vermutungen ueber das Spielfeld an. "
        "Nutze EINEN konkreten Denkhinweis zum fehlenden Uebergang: Ziel, Modell, kleiner "
        "Handlungsschritt, selbst coden, pruefen. Hoestens EINE Frage. Nie Code diktieren "
        "oder eine vollstaendige Loesung ausgeben. Kein allgemeines Lob. Antworte auf Deutsch "
        "in hoechstens 65 gesprochenen Woertern. Nur den zu sprechenden Text ausgeben.\n\n"
        f"Ziel: {ctx['goal'] or 'aktuellen Spielcode verstehen'}\n"
        f"Datei: {ctx['file'] or 'nicht erkannt'}\n"
        f"Code:\n{ctx['code']}\n"
        f"Frage: {ctx['user'] or '(keine)'}\n"
        f"Laufzeitfehler: {ctx.get('error') or '(keiner)'}\n"
    )
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False,
                          "options": {"num_predict": 135, "temperature": 0.2}}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.load(resp)
    reply = data.get("response", "").strip()
    # Reject unsolicited generated code rather than dictating it through speech.
    if not reply or "```" in reply or re.search(r"(?im)^\s*(def |while |for |if |return |move\(|plant\()", reply):
        raise ValueError("Local model did not produce a spoken coaching hint")
    return " ".join(reply.split()[:70])


class LocalPi:
    """Asynchronous drop-in for Pi's ask/poll/ready/abort/close subset."""
    def __init__(self, model="qwen3:8b", url="http://127.0.0.1:11434/api/generate", timeout=25):
        self.model, self.url, self.timeout = model, url, timeout
        self.busy = False
        self.req = 0
        self.generation = 0
        self.messages = queue.Queue()
        self.last_signature = None

    def ready(self):
        return not self.busy

    def ask(self, observation, png=None):
        ctx = context_from_observation(observation)
        signature = hashlib.sha256((ctx["file"] + ctx["code"] + ctx["user"]).encode()).hexdigest()
        self.req += 1
        self.busy = True
        self.generation += 1
        generation = self.generation
        if "weiter (" in ctx["reason"] or (signature == self.last_signature and not ctx["user"]
                                                 and "jetzt erklären" not in ctx["reason"]):
            self.messages.put((generation, "SKIP"))
            return
        self.last_signature = signature

        def work():
            try:
                msg = local_model_reply(ctx, self.model, self.url, self.timeout)
            except (OSError, ValueError, TimeoutError, KeyError, TypeError):
                msg = simple_hint(ctx)
            self.messages.put((generation, "SPRECHEN: " + msg))

        threading.Thread(target=work, daemon=True).start()

    def poll(self):
        while not self.messages.empty():
            generation, msg = self.messages.get_nowait()
            if generation != self.generation:
                continue
            self.busy = False
            return msg
        return None

    def abort(self):
        self.generation += 1
        self.busy = False

    def close(self):
        self.abort()
