#!/usr/bin/env python3
"""The TOML writer must change one value and disturb nothing else.

The shipped config is ~100 lines of explanatory comments wrapped around 34
settings. Those comments are the real documentation for every knob, so the
writer patches single lines rather than regenerating the file -- and that is
exactly the kind of thing that breaks silently. Hence these tests.
"""
import pathlib
import sys
import tomllib
import types

REPO = pathlib.Path(__file__).resolve().parent.parent
src = (REPO / "bin" / "legion-config").read_text()
LC = types.ModuleType("legion_config")
LC.__file__ = str(REPO / "bin" / "legion-config")
exec(compile(src.replace('if __name__ == "__main__":\n    sys.exit(main())', ""),
             "legion-config", "exec"), LC.__dict__)

ORIGINAL = (REPO / "config" / "legion-nav.toml").read_text()

FAILS = []


def check(label, got, want):
    ok = got == want
    print(("  PASS " if ok else "  FAIL ") + f"{label}"
          + ("" if ok else f": got={got!r} want={want!r}"))
    if not ok:
        FAILS.append(label)


print("\n1. a string value changes, and nothing else does")
out = LC.set_in_toml(ORIGINAL, "buttons", "a", "key:KEY_ENTER")
check("value changed", tomllib.loads(out)["buttons"]["a"], "key:KEY_ENTER")
check("exactly one line differs",
      sum(1 for x, y in zip(ORIGINAL.splitlines(), out.splitlines()) if x != y), 1)
check("line count unchanged", len(out.splitlines()), len(ORIGINAL.splitlines()))
check("comments survive", out.count("#"), ORIGINAL.count("#"))
check("column alignment preserved", 'a      = "key:KEY_ENTER"' in out, True)

print("\n2. every scalar type round-trips")
for section, key, value in [
    ("cursor", "max_speed", 2400.0),
    ("cursor", "tick_hz", 120),
    ("scroll", "enabled", True),
    ("scroll", "natural", False),
    ("scroll", "engage_ms", 250),
    ("triggers", "press_at", 0.65),
    ("modes", "mode_hold_seconds", 1.2),
    ("dpad_keys", "up", "key:KEY_PAGEUP"),
]:
    text = LC.set_in_toml(ORIGINAL, section, key, value)
    check(f"{section}.{key}", tomllib.loads(text)[section][key], value)

print("\n3. floats are written as floats, ints as ints")
check("1500.0 stays a float", LC.format_value(1500.0), "1500.0")
check("0.35 is not mangled", LC.format_value(0.35), "0.35")
check("float rounding is tidy", LC.format_value(0.30000000000000004), "0.3")
check("int has no decimal point", LC.format_value(200), "200")
check("bool is lowercase", (LC.format_value(True), LC.format_value(False)), ("true", "false"))
check("string is quoted", LC.format_value("exec:a b"), '"exec:a b"')

print("\n4. a commented-out example is never mistaken for the setting")
# Built as a fixture rather than leaning on the shipped prose, so rewording a
# comment in the real config cannot quietly retire this check.
fixture = (
    "[scroll]\n"
    "# Set enabled = true to turn this back on.\n"
    "#   enabled = true\n"
    "enabled = false\n"
    "deadzone = 0.35\n"
)
out = LC.set_in_toml(fixture, "scroll", "enabled", True)
check("the real key changed", tomllib.loads(out)["scroll"]["enabled"], True)
check("both comment lines survive verbatim",
      [l for l in out.splitlines() if l.startswith("#")],
      [l for l in fixture.splitlines() if l.startswith("#")])
check("exactly one line changed",
      sum(1 for x, y in zip(fixture.splitlines(), out.splitlines()) if x != y), 1)
check("the changed line is the real assignment",
      [l for l in out.splitlines() if l == "enabled = true"], ["enabled = true"])

print("\n5. a missing key is inserted into the right section")
text = LC.set_in_toml(ORIGINAL.replace("precision_factor = 0.3\n", ""),
                      "cursor", "precision_factor", 0.45)
check("inserted and parses", tomllib.loads(text)["cursor"]["precision_factor"], 0.45)
check("landed in [cursor], not elsewhere",
      tomllib.loads(text)["scroll"].get("precision_factor"), None)

print("\n6. a missing section is appended")
text = LC.set_in_toml(ORIGINAL, "brandnew", "thing", 7)
check("section created", tomllib.loads(text)["brandnew"]["thing"], 7)
check("existing sections intact", set(tomllib.loads(ORIGINAL)) <= set(tomllib.loads(text)), True)

print("\n7. writing every setting keeps all 17 bindings")
text = ORIGINAL
cfg = tomllib.loads(ORIGINAL)
for control, _ in LC.CONTROLS:
    section, key = LC.section_of(control)
    text = LC.set_in_toml(text, section, key, cfg[section][key])
for entry in LC.FEEL:
    text = LC.set_in_toml(text, entry[0], entry[1], cfg[entry[0]][entry[1]])
result = tomllib.loads(text)
check("identical to the original config", result, cfg)
check("[buttons] still has 13 entries", len(result["buttons"]), len(cfg["buttons"]))
check("[dpad_keys] still has 4 entries", len(result["dpad_keys"]), 4)
check("file is byte-identical", text, ORIGINAL)

print("\n" + ("ALL PASS" if not FAILS else f"{len(FAILS)} FAILURES: {FAILS}"))
sys.exit(1 if FAILS else 0)
