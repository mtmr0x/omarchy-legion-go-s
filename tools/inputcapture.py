#!/usr/bin/env python3
"""Record everything every input device reports, to identify an unknown input.

On Wayland a scroll can only reach an application two ways:

  1. the compositor sends one, having got it from libinput -> evdev, or
  2. the application synthesises one from touch events it received.

This captures both. It opens every readable /dev/input/event* node, logs every
event with its device and decoded name, and separately samples the gamepad's
absolute axes so stick position is visible even when a daemon holds an
exclusive grab on it.

Usage:

    # 1. Is legion-nav involved at all? Stop it, then reproduce the problem.
    python3 tools/inputcapture.py --stop-daemon --seconds 20

    # 2. If it still happens with the daemon stopped, legion-nav is innocent
    #    and the culprit is whatever showed up in the log.
    python3 tools/inputcapture.py --seconds 20

Everything is written to a log file as well as the screen.
"""
import argparse
import collections
import os
import selectors
import subprocess
import sys
import time

import evdev
from evdev import ecodes as e

VENDOR, PRODUCTS = 0x1A86, (0xE310, 0xE311)

TYPE_NAMES = {e.EV_KEY: "KEY", e.EV_REL: "REL", e.EV_ABS: "ABS",
              e.EV_SW: "SW", e.EV_MSC: "MSC", e.EV_LED: "LED", e.EV_SND: "SND"}

# Events that actually mean something to a human, versus axis jitter.
NOTABLE_REL = set(
    v for k, v in vars(e).items() if k.startswith("REL_")
)


def code_name(etype: int, code: int) -> str:
    table = {e.EV_KEY: e.KEY, e.EV_REL: e.REL, e.EV_ABS: e.ABS,
             e.EV_SW: e.SW, e.EV_MSC: e.MSC}.get(etype)
    if not table:
        return str(code)
    name = table.get(code, code)
    return name[0] if isinstance(name, (list, tuple)) else str(name)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seconds", type=float, default=20.0, help="capture duration")
    parser.add_argument("--stop-daemon", action="store_true",
                        help="stop legion-nav during the capture, then restart it")
    parser.add_argument("--log", default=None, help="log file (default: ./inputcapture-<time>.log")
    args = parser.parse_args()

    sys.stdout.reconfigure(line_buffering=True)
    log_path = args.log or f"inputcapture-{time.strftime('%H%M%S')}.log"
    log = open(log_path, "w")

    def emit(line: str) -> None:
        print(line)
        log.write(line + "\n")

    stopped = False
    if args.stop_daemon:
        stopped = subprocess.run(
            ["systemctl", "--user", "is-active", "--quiet", "legion-nav"]).returncode == 0
        if stopped:
            subprocess.run(["systemctl", "--user", "stop", "legion-nav"], check=False)
            emit("legion-nav STOPPED for this capture -- the pad is no longer grabbed.")
            emit("If the problem still happens now, legion-nav is not causing it.\n")
            time.sleep(0.5)

    try:
        devices, unreadable, pad = [], [], None
        for path in sorted(evdev.list_devices()):
            try:
                dev = evdev.InputDevice(path)
            except OSError as exc:
                unreadable.append(f"{path} ({exc.strerror})")
                continue
            devices.append(dev)
            if dev.info.vendor == VENDOR and dev.info.product in PRODUCTS:
                pad = dev

        emit(f"Capturing {len(devices)} input devices for {args.seconds:g}s -> {log_path}\n")
        for dev in devices:
            emit(f"  {dev.path:<20} {dev.name}")
        if unreadable:
            emit("\n  NOT READABLE (would be invisible to this capture):")
            for item in unreadable:
                emit(f"    {item}")
        emit("")

        if pad:
            emit(f"Gamepad axes sampled from {pad.path} (works even under a grab).")
        emit("\n>>> Reproduce the problem now: rotate the device. <<<\n")

        selector = selectors.DefaultSelector()
        for dev in devices:
            selector.register(dev.fd, selectors.EVENT_READ, dev)

        counts = collections.Counter()
        axis_peak = collections.defaultdict(float)
        started = time.monotonic()
        deadline = started + args.seconds

        while time.monotonic() < deadline:
            for key, _ in selector.select(0.05):
                dev = key.data
                try:
                    events = list(dev.read())
                except OSError:
                    continue
                for ev in events:
                    if ev.type == e.EV_SYN:
                        continue
                    counts[(dev.name, TYPE_NAMES.get(ev.type, ev.type),
                            code_name(ev.type, ev.code))] += 1
                    stamp = time.monotonic() - started
                    # Print anything a human would call an input; axis jitter is
                    # counted but not printed, or it would drown everything else.
                    if ev.type in (e.EV_KEY, e.EV_REL, e.EV_SW) or (
                        ev.type == e.EV_ABS and ev.code in (
                            e.ABS_MT_POSITION_X, e.ABS_MT_POSITION_Y)):
                        emit(f"[{stamp:6.2f}s] {dev.name:<28} "
                             f"{TYPE_NAMES.get(ev.type, ev.type):<3} "
                             f"{code_name(ev.type, ev.code):<22} value={ev.value}")

            if pad:
                for code in (e.ABS_X, e.ABS_Y, e.ABS_RX, e.ABS_RY):
                    value = pad.absinfo(code).value
                    pct = abs(value / (32767 if value > 0 else 32768)) * 100
                    axis_peak[code_name(e.EV_ABS, code)] = max(
                        axis_peak[code_name(e.EV_ABS, code)], pct)

        emit("\n" + "=" * 70)
        emit("SUMMARY -- every event seen, by device")
        emit("=" * 70)
        if not counts:
            emit("  NOTHING. No input device reported anything at all.")
        for (name, etype, code), n in counts.most_common():
            emit(f"  {n:>7}  {name:<30} {etype:<4} {code}")

        if pad:
            emit("\nPeak gamepad stick deflection during the capture:")
            for axis in ("ABS_X", "ABS_Y", "ABS_RX", "ABS_RY"):
                peak = axis_peak.get(axis, 0.0)
                note = ""
                if axis in ("ABS_RX", "ABS_RY"):
                    note = "  <-- scroll needs >20%" if peak <= 20 else "  <-- PAST the scroll deadzone"
                emit(f"  {axis:<7} {peak:5.1f}%{note}")

        touched = any(code == "BTN_TOUCH" for (_, _, code) in counts)
        wheeled = any(code.startswith("REL_WHEEL") or code.startswith("REL_HWHEEL")
                      for (_, _, code) in counts)
        emit("\nREADING:")
        emit(f"  touchscreen contact : {'YES' if touched else 'no'}")
        emit(f"  wheel events        : {'YES' if wheeled else 'no'}")
        if touched and not wheeled:
            emit("  => The touchscreen is the source. Apps scroll from touch directly;")
            emit("     no wheel event is ever generated, which is why it looks invisible.")
        elif wheeled:
            emit("  => Something emitted real wheel events; see which device above.")
        elif not counts:
            emit("  => No input at all was reported. If the screen still scrolled, the")
            emit("     scroll did not come through the kernel input layer.")
    finally:
        log.close()
        if stopped:
            subprocess.run(["systemctl", "--user", "start", "legion-nav"], check=False)
            print("\nlegion-nav restarted.")
        print(f"Log saved to {os.path.abspath(log_path)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
