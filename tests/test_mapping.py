"""Exercise legion-nav's mapping logic with stubbed uinput + a fake pad."""
import sys, types, time
import evdev
from evdev import ecodes as e

# --- stub uinput before the module builds any -------------------------------
class FakeUInput:
    def __init__(self, caps, name="", vendor=0, product=0):
        self.name, self.caps, self.log = name, caps, []
    def write(self, t, c, v): self.log.append((t, c, v))
    def syn(self): pass
    def close(self): pass

evdev.UInput = FakeUInput

mod = types.ModuleType("ln"); mod.__file__ = "bin/legion-nav"
src = open("bin/legion-nav").read().replace('if __name__ == "__main__":\n    sys.exit(main())', '')
exec(compile(src, "legion-nav", "exec"), mod.__dict__)

FAILS = []
def check(label, got, want):
    ok = got == want
    print(("  PASS " if ok else "  FAIL ") + f"{label}: got={got!r} want={want!r}")
    if not ok: FAILS.append(label)

cfg = mod.load_config("config/legion-nav.toml")

class FakeDev:
    path, name = "/dev/input/fake", "Legion Go S"
    def __init__(self): self.grabs = []
    def grab(self): self.grabs.append("grab")
    def ungrab(self): self.grabs.append("ungrab")
    def close(self): pass

nav = mod.Nav.__new__(mod.Nav)          # skip __init__: no control socket
nav.cfg, nav.verbose = cfg, False
nav.actions = mod.build_actions(cfg)
nav.virtual = mod.Virtual(nav.actions)
nav.hypr = mod.Hypr()
nav.dev = FakeDev()
nav.grabbed = False
nav.mode = "game"; nav.override = None; nav.override_class = None; nav.auto_mode = "desktop"
nav.axes = {e.ABS_X:0, e.ABS_Y:0, e.ABS_RX:0, e.ABS_RY:0, e.ABS_Z:0, e.ABS_RZ:0,
            e.ABS_HAT0X:0, e.ABS_HAT0Y:0}
nav.down = set(); nav.precision = False; nav.legion_since = None
nav.cursor_frac = [0.0, 0.0]; nav.running = True
nav.scroll_since = None
nav.inhibit_until = 0.0
nav.config_path = None
nav.spawned = []
nav.spawn = lambda cmd: nav.spawned.append(cmd)

def ev(t, c, v):
    return types.SimpleNamespace(type=t, code=c, value=v)

kb, ptr = nav.virtual.keyboard, nav.virtual.pointer

print("\n1. desktop mode grabs the pad")
nav.apply_mode()
check("mode", nav.mode, "desktop")
check("grab called", nav.dev.grabs, ["grab"])

print("\n2. A -> left click, B -> right click (pointer only)")
ptr.log.clear(); kb.log.clear()
nav.handle_event(ev(e.EV_KEY, e.BTN_A, 1))
nav.handle_event(ev(e.EV_KEY, e.BTN_A, 0))
nav.handle_event(ev(e.EV_KEY, e.BTN_B, 1))
nav.handle_event(ev(e.EV_KEY, e.BTN_B, 0))
check("pointer events", ptr.log, [(e.EV_KEY, e.BTN_LEFT, 1), (e.EV_KEY, e.BTN_LEFT, 0),
                                  (e.EV_KEY, e.BTN_RIGHT, 1), (e.EV_KEY, e.BTN_RIGHT, 0)])
check("keyboard untouched", kb.log, [])

print("\n3. Y -> Enter on the keyboard, X -> on-screen keyboard")
ptr.log.clear(); kb.log.clear(); nav.spawned.clear()
nav.handle_event(ev(e.EV_KEY, e.BTN_Y, 1))
nav.handle_event(ev(e.EV_KEY, e.BTN_Y, 0))
check("keyboard events", kb.log, [(e.EV_KEY, e.KEY_ENTER, 1), (e.EV_KEY, e.KEY_ENTER, 0)])
check("pointer untouched", ptr.log, [])
nav.handle_event(ev(e.EV_KEY, e.BTN_X, 1))
nav.handle_event(ev(e.EV_KEY, e.BTN_X, 0))
check("X spawns the OSK once", nav.spawned, ["legion-osk toggle"])

print("\n3b. the face buttons use the legacy 307=X / 308=Y numbering")
check("x is 307", mod.BUTTONS["x"], 307)
check("y is 308", mod.BUTTONS["y"], 308)

print("\n4. D-pad -> arrow keys (hold, so the compositor repeats)")
kb.log.clear()
nav.handle_event(ev(e.EV_ABS, e.ABS_HAT0Y, -1))
nav.handle_event(ev(e.EV_ABS, e.ABS_HAT0Y, 0))
nav.handle_event(ev(e.EV_ABS, e.ABS_HAT0X, 1))
nav.handle_event(ev(e.EV_ABS, e.ABS_HAT0X, 0))
check("arrows", kb.log, [(e.EV_KEY, e.KEY_UP, 1), (e.EV_KEY, e.KEY_UP, 0),
                         (e.EV_KEY, e.KEY_RIGHT, 1), (e.EV_KEY, e.KEY_RIGHT, 0)])

print("\n5. analog trigger hysteresis (press .5 / release .35)")
# LT is a held key, so both edges are visible.
kb.log.clear()
for raw in (100, 130, 200, 255, 120, 100, 80):   # 0.39 .51 .78 1.0 .47 .39 .31
    nav.handle_event(ev(e.EV_ABS, e.ABS_Z, raw))
check("LT pressed once then released once", kb.log,
      [(e.EV_KEY, e.KEY_ESC, 1), (e.EV_KEY, e.KEY_ESC, 0)])

# Crossing down to .47 must NOT release: that is between release_at and press_at.
kb.log.clear()
for raw in (255, 120, 255):                      # 1.0 -> .47 -> 1.0
    nav.handle_event(ev(e.EV_ABS, e.ABS_Z, raw))
check("no chatter in the hysteresis band", kb.log, [(e.EV_KEY, e.KEY_ESC, 1)])
nav.handle_event(ev(e.EV_ABS, e.ABS_Z, 0))

print("\n5b. RT opens the window menu, once per pull")
nav.spawned.clear()
for raw in (0, 200, 255, 200, 0):
    nav.handle_event(ev(e.EV_ABS, e.ABS_RZ, raw))
check("menu summoned once", nav.spawned, ["omarchy menu toggle window"])

print("\n6. exec actions fire on press only")
nav.spawned.clear()
nav.handle_event(ev(e.EV_KEY, e.BTN_TR, 1))
nav.handle_event(ev(e.EV_KEY, e.BTN_TR, 0))
check("spawned", nav.spawned, ["hyprctl dispatch 'hl.dsp.focus({ workspace = \"e+1\" })'"])

print("\n7. left stick moves the cursor")
ptr.log.clear()
nav.axes[e.ABS_X] = 32767; nav.axes[e.ABS_Y] = -32768
nav.tick(0.1)                                  # 100 ms at full deflection
moves = [(c, v) for t, c, v in ptr.log if t == e.EV_REL]
check("moved right and up by ~150px", moves, [(e.REL_X, 150), (e.REL_Y, -150)])

print("\n7b. scroll is on by default, but a knock is ignored")
# Picking the machine up throws the stick past any deadzone from sheer inertia,
# which scrolled the page on its own. engage_ms is what separates that from a
# deliberate scroll, so the feature ships on with the delay rather than off.
check("enabled in the shipped config", cfg["scroll"]["enabled"], True)
nav.axes[e.ABS_X] = nav.axes[e.ABS_Y] = 0
nav.axes[e.ABS_RY] = -32768                    # stick fully up
nav.scroll_since = None

# A transient deflection -- shorter than engage_ms -- must produce nothing.
ptr.log.clear()
nav.tick(0.005)
nav.tick(0.005)
check("brief deflection ignored", [(c, v) for t, c, v in ptr.log if t == e.EV_REL], [])

print("\n7c. a deflection held past engage_ms scrolls normally")

# Held past engage_ms, it scrolls normally.
ptr.log.clear()
nav.scroll_since = time.monotonic() - 1.0
nav.tick(1.0)
rel = [(c, v) for t, c, v in ptr.log if t == e.EV_REL]
hi = sum(v for c, v in rel if c == e.REL_WHEEL_HI_RES)
lo = sum(v for c, v in rel if c == e.REL_WHEEL)
check("hi-res units == 18 notches", hi, 18 * 120)
check("legacy notches == 18", lo, 18)
check("scrolls up (positive)", hi > 0, True)

# Returning to centre re-arms the delay for next time.
nav.axes[e.ABS_RY] = 0
nav.tick(0.005)
check("delay re-armed on release", nav.scroll_since, None)

print("\n7d. disabling it silences the right stick entirely")
nav.cfg["scroll"]["enabled"] = False
nav.axes[e.ABS_RY] = -32768
nav.scroll_since = None
ptr.log.clear()
nav.tick(1.0)
nav.tick(1.0)
check("nothing emitted", [(c, v) for t, c, v in ptr.log if t == e.EV_REL], [])
check("delay state cleared", nav.scroll_since, None)
nav.axes[e.ABS_RY] = 0

print("\n8. precision mode (R3) slows the cursor")
nav.axes[e.ABS_RY] = 0
nav.handle_event(ev(e.EV_KEY, e.BTN_THUMBR, 1))
check("precision on", nav.precision, True)
ptr.log.clear(); nav.cursor_frac = [0.0, 0.0]
nav.axes[e.ABS_X] = 32767
nav.tick(0.1)
check("150px -> 45px", [(c, v) for t, c, v in ptr.log if t == e.EV_REL], [(e.REL_X, 45)])
nav.handle_event(ev(e.EV_KEY, e.BTN_THUMBR, 0))

print("\n9. game mode releases the grab and emits nothing")
nav.axes[e.ABS_X] = 0
nav.auto_mode = "game"; nav.apply_mode()
check("mode", nav.mode, "game")
check("ungrab called", nav.dev.grabs, ["grab", "ungrab"])
ptr.log.clear(); kb.log.clear(); nav.spawned.clear()
nav.handle_event(ev(e.EV_KEY, e.BTN_A, 1))
nav.handle_event(ev(e.EV_KEY, e.BTN_TR, 1))
nav.axes[e.ABS_X] = 32767; nav.tick(0.5)
check("no pointer output", ptr.log, [])
check("no key output", kb.log, [])
check("no commands run", nav.spawned, [])

print("\n10. holding Legion toggles out of game mode")
# This is the only escape hatch that works from inside a game: in game mode the
# pad is released, so nothing else the daemon does is running.
check("bound in the shipped config",
      mod.build_actions(cfg).get("legion").value, "mode_hold")
nav.handle_event(ev(e.EV_KEY, e.BTN_MODE, 1))
check("hold timer armed", nav.legion_since is not None, True)
nav.legion_since = time.monotonic() - 1.0      # pretend it has been held
nav.tick(0.005)
check("back to desktop", nav.mode, "desktop")
check("override set", nav.override, "desktop")

print("\n11. switching modes releases anything still held")
nav.handle_event(ev(e.EV_KEY, e.BTN_A, 1))
check("left button is held", ("btn", e.BTN_LEFT) in nav.virtual.held, True)
ptr.log.clear()
nav.override = None; nav.auto_mode = "game"; nav.apply_mode()
check("released on switch", (e.EV_KEY, e.BTN_LEFT, 0) in ptr.log, True)
check("nothing left held", nav.virtual.held, set())

print("\n12. game-class matching")
nav.override = None
for klass, fullscreen, content, want in [
    ("foot", 0, "none", "desktop"),
    ("steam", 0, "none", "game"),
    ("steam_app_620", 0, "none", "game"),
    ("SomeGame", 2, "none", "game"),          # fullscreen heuristic
    ("SomeGame", 0, "game", "game"),          # wayland content-type hint
    ("chromium", 2, "video", "game"),         # fullscreen, no allowlist entry
]:
    nav.hypr.active_window = lambda k=klass, f=fullscreen, c=content: {
        "class": k, "fullscreen": f, "contentType": c}
    nav.evaluate_window()
    check(f"{klass} fs={fullscreen} ct={content}", nav.auto_mode, want)

print("\n13. desktop_classes exempts a class from the fullscreen rule")
nav.cfg["modes"]["desktop_classes"] = ["chromium"]
nav.hypr.active_window = lambda: {"class": "chromium", "fullscreen": 2, "contentType": "none"}
nav.evaluate_window()
check("chromium fullscreen stays desktop", nav.auto_mode, "desktop")

print("\n14. an override is cleared by moving focus elsewhere")
nav.set_override("game"); check("override_class recorded", nav.override_class, "chromium")
nav.hypr.active_window = lambda: {"class": "foot", "fullscreen": 0, "contentType": "none"}
nav.evaluate_window()
check("override cleared", nav.override, None)
check("mode followed auto", nav.mode, "desktop")

print("\n" + ("ALL PASS" if not FAILS else f"{len(FAILS)} FAILURES: {FAILS}"))
sys.exit(1 if FAILS else 0)
