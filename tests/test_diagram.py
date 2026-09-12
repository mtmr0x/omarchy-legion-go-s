#!/usr/bin/env python3
"""The device diagram and its highlight spans must stay in sync.

render_diagram() reports where each control sits so the UI can highlight it.
If a label changes length and the spans are computed wrong, the highlight lands
on the wrong glyph -- silently. These tests pin that down.
"""
import pathlib
import sys
import types

REPO = pathlib.Path(__file__).resolve().parent.parent
src = (REPO / "bin" / "legion-config").read_text()
LC = types.ModuleType("legion_config")
LC.__file__ = str(REPO / "bin" / "legion-config")
exec(compile(src.replace('if __name__ == "__main__":\n    sys.exit(main())', ""),
             "legion-config", "exec"), LC.__dict__)

FAILS = []


def check(label, got, want):
    ok = got == want
    print(("  PASS " if ok else "  FAIL ") + f"{label}"
          + ("" if ok else f": got={got!r} want={want!r}"))
    if not ok:
        FAILS.append(label)


lines, spans = LC.render_diagram()

print("\n1. the art is rectangular")
check("all rows the same width", len({len(line) for line in lines}), 1)
check("at least the minimum width", len(lines[0]) >= LC.MIN_DIAGRAM_WIDTH, True)

print("\n2. every drawn control appears, exactly once")
check("span count matches label count", len(spans), len(LC.LABELS))
check("no drawn control is missing", sorted(spans), sorted(LC.LABELS))
for control in LC.LABELS:
    label = LC.LABELS[control]
    occurrences = sum(line.count(label) for line in lines)
    if control in ("a", "b", "x", "y"):
        continue          # single letters also occur inside SEL/STA/LGN
    check(f"{control} drawn once", occurrences, 1)

print("\n2b. controls that are not drawn are still bindable")
for control in LC.NOT_ON_DIAGRAM:
    check(f"{control} absent from the art", control not in spans, True)
    check(f"{control} still editable", control in LC.CONTROL_NAMES, True)
check("drawn controls are all real controls",
      set(LC.LABELS) <= set(LC.CONTROL_NAMES), True)

print("\n3. each span points at its own label")
for control, (row, col, size) in sorted(spans.items()):
    check(f"{control} span is correct", lines[row][col:col + size], LC.LABELS[control])

print("\n4. spans never overlap")
taken = {}
overlaps = []
for control, (row, col, size) in spans.items():
    for x in range(col, col + size):
        if (row, x) in taken:
            overlaps.append((control, taken[(row, x)]))
        taken[(row, x)] = control
check("no two controls share a cell", overlaps, [])

print("\n5. spans land inside the drawn area")
outside = [c for c, (r, col, size) in spans.items()
           if r >= len(lines) or col + size > len(lines[r])]
check("every span is in bounds", outside, [])

print("\n6. the frame is intact")
check("top border", lines[2].strip().startswith("╭") and lines[2].strip().endswith("╮"), True)
check("bottom border", lines[-1].strip().startswith("╰") and lines[-1].strip().endswith("╯"), True)
check("side walls present", all("│" in line for line in lines[3:7]), True)

print("\n7. every control resolves to a readable action")
cfg = LC.LN.load_config(str(REPO / "config" / "legion-nav.toml"))
for control, _ in LC.CONTROLS:
    described = LC.describe(LC.binding_of(cfg, control))
    check(f"{control} described", bool(described) and described != "none", True)

print("\n" + ("ALL PASS" if not FAILS else f"{len(FAILS)} FAILURES: {FAILS}"))
sys.exit(1 if FAILS else 0)
