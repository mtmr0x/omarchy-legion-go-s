#!/usr/bin/env python3
"""Drive legion-config in a real pty and assert on what it paints.

A curses app can only really be tested by running it, so this opens a pty at a
given size, feeds it keystrokes, and reads back the screen. It edits a throwaway
copy of the config via -c, so the real one is never touched.
"""
import fcntl
import os
import pathlib
import pty
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import termios
import time
import tomllib

REPO = pathlib.Path(__file__).resolve().parent.parent
ANSI = re.compile(r"\x1b\[[0-9;?]*[a-zA-Z]|\x1b[()][B0]|\x1b[=>]")

# curses turns on application cursor mode (smkx), so a real terminal sends
# ESC O x for the arrows, not ESC [ x.
UP, DOWN, LEFT, RIGHT = b"\x1bOA", b"\x1bOB", b"\x1bOD", b"\x1bOC"
ENTER, ESC = b"\r", b"\x1b"

FAILS = []


def check(label, ok):
    print(("  PASS " if ok else "  FAIL ") + label)
    if not ok:
        FAILS.append(label)


def run(config, keys, cols=128, rows=30, settle=1.0):
    primary, secondary = pty.openpty()
    fcntl.ioctl(secondary, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
    proc = subprocess.Popen(
        ["python3", str(REPO / "bin" / "legion-config"), "-c", str(config)],
        stdin=secondary, stdout=secondary, stderr=secondary,
        env=dict(os.environ, TERM="xterm-256color"), close_fds=True)
    os.close(secondary)
    os.set_blocking(primary, False)

    buf = []

    def drain():
        try:                       # EIO just means the child closed the pty
            while True:
                chunk = os.read(primary, 65536)
                if not chunk:
                    return
                buf.append(chunk)
        except (BlockingIOError, OSError):
            return

    time.sleep(settle)
    drain()
    for key in keys:
        try:
            os.write(primary, key)
        except OSError:
            break
        time.sleep(0.3)
        drain()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
    drain()
    os.close(primary)
    return ANSI.sub("", b"".join(buf).decode("utf-8", "replace")), proc.returncode


def scratch():
    handle = tempfile.NamedTemporaryFile(suffix=".toml", delete=False)
    handle.close()
    shutil.copy(REPO / "config" / "legion-nav.toml", handle.name)
    return handle.name


print("\n1. the main screen renders on the handheld panel (128x30)")
# Select and Legion are bindable but deliberately not drawn.
cfg = scratch()
text, code = run(cfg, [b"q"])
for want in ["legion-nav", "Buttons", "Feel", "Save", "Revert", "Quit"]:
    check(f"shows {want!r}", want in text)
for want in ["LB", "RB", "LT", "RT", "STA", "L3", "R3", "▲", "╭", "╰"]:
    check(f"diagram has {want!r}", want in text)
check("bindings are described in words", "On-screen keyboard" in text)
check("quits on q", code == 0)

print("\n2. the Feel tab is reachable with arrows alone")
text, code = run(cfg, [UP, RIGHT, DOWN, b"q"])
check("cursor speed row", "Cursor speed" in text)
check("slider drawn", "▮" in text and "▯" in text)
check("units shown", "px/s" in text)
check("scroll safeguards exposed", "Scroll engage delay" in text)
check("quits on q", code == 0)

print("\n3. the action picker opens, scrolls, and cancels")
text, code = run(cfg, [ENTER, UP, ESC, b"q"])
check("picker chrome shown", "esc cancel" in text)
check("wrapping up reaches Custom", "Custom" in text)
check("quits on q", code == 0)

print("\n4. escape backs out instead of quitting")
text, code = run(cfg, [ESC, ESC, b"q"])
check("survived two escapes and quit on q", code == 0)
check("tab bar still drawn", "Buttons" in text)

print("\n5. editing a binding and saving rewrites exactly one line")
cfg = scratch()
before = pathlib.Path(cfg).read_text()
# A is 'Left click' (index 0); one DOWN in the picker selects 'Right click'.
text, code = run(cfg, [ENTER, DOWN, ENTER, b"s", b"q"])
after = pathlib.Path(cfg).read_text()
parsed = tomllib.loads(after)
check("A was rebound", parsed["buttons"]["a"] == "btn:BTN_RIGHT")
check("exactly one line changed",
      sum(1 for x, y in zip(before.splitlines(), after.splitlines()) if x != y) == 1)
check("comments preserved", after.count("#") == before.count("#"))
check("all 13 buttons survive", len(parsed["buttons"]) == 13)
check("all 4 dpad keys survive", len(parsed["dpad_keys"]) == 4)
check("a backup was written", len(list(pathlib.Path(cfg).parent.glob(
    pathlib.Path(cfg).name + ".bak.*"))) >= 1)
check("quits on q", code == 0)

print("\n6. it survives a narrow split and a short terminal")
for cols, rows in ((61, 30), (80, 16), (200, 50)):
    text, code = run(cfg, [DOWN, b"q"], cols=cols, rows=rows)
    check(f"{cols}x{rows} renders and exits", "Buttons" in text and code == 0)

print("\n7. --print works with no terminal at all")
out = subprocess.run(["python3", str(REPO / "bin" / "legion-config"), "-c", cfg, "--print"],
                     capture_output=True, text=True)
check("exit 0", out.returncode == 0)
check("diagram present", "╭" in out.stdout and "STA" in out.stdout)
check("all 17 controls listed", out.stdout.count("\n  ") >= 17)

print("\n" + ("ALL PASS" if not FAILS else f"{len(FAILS)} FAILURES: {FAILS}"))
sys.exit(1 if FAILS else 0)
