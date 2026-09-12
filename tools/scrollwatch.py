#!/usr/bin/env python3
"""Find out what is actually generating scroll on this machine.

There are three plausible sources, and this tells them apart:

  1. the right thumbstick      -> legion-nav emits wheel events
  2. any other pointing device -> it emits wheel events itself
  3. the touchscreen           -> no wheel event exists at all; the app turns a
                                  touch-drag into a scroll on its own, so the
                                  only evidence is screen contact

Reading the pad's stick position works even though legion-nav holds an exclusive
grab, because absinfo is an ioctl rather than part of the event stream.

    python3 tools/scrollwatch.py
"""
import selectors
import sys
import time

import evdev
from evdev import ecodes as e

VENDOR, PRODUCTS = 0x1A86, (0xE310, 0xE311)
WHEELS = {
    e.REL_WHEEL: "REL_WHEEL", e.REL_HWHEEL: "REL_HWHEEL",
    e.REL_WHEEL_HI_RES: "REL_WHEEL_HI_RES", e.REL_HWHEEL_HI_RES: "REL_HWHEEL_HI_RES",
}


def main() -> int:
    sys.stdout.reconfigure(line_buffering=True)

    pad = None
    wheel_devs, touch_devs = [], []
    for path in evdev.list_devices():
        try:
            dev = evdev.InputDevice(path)
        except OSError:
            continue
        caps = dev.capabilities()
        if dev.info.vendor == VENDOR and dev.info.product in PRODUCTS:
            pad = dev
        if e.EV_REL in caps:
            wheel_devs.append(dev)
        abs_codes = [c for c, _ in caps.get(e.EV_ABS, [])]
        if e.ABS_MT_POSITION_X in abs_codes or e.BTN_TOUCH in caps.get(e.EV_KEY, []):
            touch_devs.append(dev)

    print("Wheel events watched on:")
    for dev in wheel_devs:
        print(f"  {dev.path:<20} {dev.name}")
    print("\nScreen/pad contact watched on:")
    for dev in touch_devs:
        print(f"  {dev.path:<20} {dev.name}")
    print(f"\nRight stick read from: {pad.path if pad else 'NOT FOUND'}")
    print("\n--- Hold the device with both thumbs OFF the sticks and rotate it. ---")
    print("--- Try it once gripping the screen bezel, once holding only the grips. ---")
    print("Ctrl-C to stop.\n")

    def stick() -> str:
        if not pad:
            return "stick unknown"
        parts = []
        for code, label in ((e.ABS_RX, "RX"), (e.ABS_RY, "RY")):
            value = pad.absinfo(code).value
            parts.append(f"{label}={value / (32767 if value > 0 else 32768) * 100:+6.1f}%")
        return " ".join(parts)

    selector = selectors.DefaultSelector()
    seen = {}
    for dev in wheel_devs + touch_devs:       # InputDevice is not hashable
        seen.setdefault(dev.path, dev)
    for dev in seen.values():
        selector.register(dev.fd, selectors.EVENT_READ, dev)

    scrolls = touches = 0
    peak = 0.0
    touching: dict[str, int] = {}
    last_summary = time.monotonic()

    try:
        while True:
            for key, _ in selector.select(0.05):
                dev = key.data
                try:
                    events = list(dev.read())
                except OSError:
                    continue
                for event in events:
                    if event.type == e.EV_REL and event.code in WHEELS:
                        scrolls += 1
                        print(f"SCROLL  {dev.name:<26} {WHEELS[event.code]:<18} "
                              f"value={event.value:<6} | right stick: {stick()}")
                    elif event.type == e.EV_KEY and event.code == e.BTN_TOUCH:
                        if event.value:
                            touches += 1
                            touching[dev.path] = 0
                            print(f"TOUCH   {dev.name:<26} contact DOWN "
                                  f"-- a drag from here scrolls without any wheel event")
                        else:
                            moved = touching.pop(dev.path, 0)
                            print(f"TOUCH   {dev.name:<26} contact UP after {moved} move events")
                    elif event.type == e.EV_ABS and event.code in (
                        e.ABS_MT_POSITION_X, e.ABS_MT_POSITION_Y, e.ABS_X, e.ABS_Y
                    ) and dev.path in touching:
                        touching[dev.path] += 1

            if pad:
                for code in (e.ABS_RX, e.ABS_RY):
                    value = pad.absinfo(code).value
                    peak = max(peak, abs(value / (32767 if value > 0 else 32768)) * 100)

            now = time.monotonic()
            if now - last_summary >= 5.0:
                last_summary = now
                print(f"  ... {scrolls} wheel events, {touches} screen contacts; "
                      f"peak right-stick deflection {peak:.1f}% (needs > 20% to scroll)")
    except KeyboardInterrupt:
        print(f"\nTotals: {scrolls} wheel events, {touches} screen contacts, "
              f"peak right-stick deflection {peak:.1f}%")
        if touches and not scrolls:
            print("=> The touchscreen is the source: contact happened, no wheel event did.")
        elif scrolls and peak > 20:
            print("=> The right stick is the source: it was deflected past the deadzone.")
        elif scrolls and peak <= 20:
            print("=> Wheel events with the stick at rest -- another device is scrolling.")
        else:
            print("=> Nothing detected. Try again and reproduce the scrolling while it runs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
