#!/usr/bin/python3
"""Smoke-Test Sprache: tutor.say() startet Piper/afplay, tutor.hush() bricht sie ab.

Spielt hier bewusst kurz Audio ab (max. zwei kurze Sätze), wie im Auftrag erlaubt.
Läuft komplett in einem eigenen TUTOR_STATE-Tempdir, fasst den echten Tutor nicht an.
Aufruf: /usr/bin/python3 tests/smoke_speech.py
"""
import os, shutil, subprocess, sys, tempfile, time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = tempfile.mkdtemp(prefix="tutor-smoke-speech-")
os.environ["TUTOR_STATE"] = STATE
sys.path.insert(0, REPO)
import tutor  # noqa: E402


def audio_procs(pgid):
    """Piper/afplay-Prozesse genau in der Prozessgruppe des Sprachjobs."""
    r = subprocess.run(["pgrep", "-g", str(pgid), "-l"], capture_output=True, text=True)
    return [l for l in r.stdout.splitlines() if ("piper" in l or "afplay" in l)]


def main():
    ok = True

    def check(cond, msg):
        nonlocal ok
        ok = ok and bool(cond)
        print("%s %s" % ("PASS" if cond else "FAIL", msg))

    text = "Der Tutor spricht jetzt zwei kurze Testsätze. Danach bricht dieser Test die Sprache sofort ab."
    tutor.say(text)
    pgid = int(tutor.F_SAYPID.read_text())
    check(tutor.speaking() is True, "speaking() ist True direkt nach say()")
    print("       Sprachgruppe pgid=%d" % pgid)

    found, t0 = None, time.time()
    while time.time() - t0 < 2.0:
        found = audio_procs(pgid)
        if found:
            break
        time.sleep(0.1)
    check(bool(found), "piper oder afplay läuft nach say() (2 s): %s" % (found or "-"))

    tutor.hush()
    check(tutor.speaking() is False, "speaking() ist False direkt nach hush()")
    deadline = time.time() + 2.0
    while audio_procs(pgid) and time.time() < deadline:
        time.sleep(0.1)
    rest = audio_procs(pgid)
    check(not rest, "kein piper/afplay aus der Gruppe nach hush() (2 s): %s" % (rest or "-"))
    check(tutor.speaking() is False, "speaking() ist False nach hush()")
    print("ERGEBNIS:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    finally:
        shutil.rmtree(STATE, ignore_errors=True)
