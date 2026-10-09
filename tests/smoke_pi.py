#!/usr/bin/python3
"""Smoke-Test Pi-RPC: tutor.Pi() startet, ask()/poll() liefert Text, abort() stürzt nicht ab,
close() beendet den Prozess.

Schiebt kurzen Text ohne Bild durch die echte Pi-RPC-Schleife (Timeout 90 s pro Antwort).
Läuft in eigenem TUTOR_STATE-Tempdir. Aufruf: /usr/bin/python3 tests/smoke_pi.py
"""
import os, shutil, sys, tempfile, time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = tempfile.mkdtemp(prefix="tutor-smoke-pi-")
os.environ["TUTOR_STATE"] = STATE
sys.path.insert(0, REPO)
import tutor  # noqa: E402

TIMEOUT = 90


def main():
    ok = True

    def check(cond, msg):
        nonlocal ok
        ok = ok and bool(cond)
        print("%s %s" % ("PASS" if cond else "FAIL", msg))

    pi = tutor.Pi()
    try:
        pi.ask("Antworte mit genau dem Wort: HALLO", None)
        t0, text = time.time(), None
        while time.time() - t0 < TIMEOUT:
            try:
                text = pi.poll()
            except RuntimeError as e:
                check(False, "Pi-Absturz beim Warten: %s" % e)
                return 1
            if text is not None:
                break
            time.sleep(0.5)
        check(bool(text and text.strip()), "Antwort in %.1f s nicht leer: %r" % (time.time() - t0, text))
        check(pi.proc.poll() is None, "Pi-Prozess lebt nach erster Antwort")

        pi.ask("Zweite Anfrage, bitte sofort verwerfen.", None)
        pi.abort()
        time.sleep(0.3)
        check(pi.proc.poll() is None, "kein Absturz nach ask()+abort()")
    finally:
        pi.close()

    check(pi.proc.poll() is not None, "close() beendet Pi (poll() ist nicht None)")

    print("ERGEBNIS:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    finally:
        shutil.rmtree(STATE, ignore_errors=True)
