# legion-nav

Drive the Omarchy desktop with the built-in gamepad of a **Lenovo Legion Go S**
(83L3) — left stick as mouse, D-pad as arrow keys, A to select — and get out of
the way automatically when a game takes focus.

Built for Arch + Hyprland (Wayland). No Steam, no gamescope, no Handheld Daemon
required.

---

## What it does

`legion-nav` reads the pad directly from evdev and re-emits it as a virtual
mouse and keyboard through `uinput`.

In **desktop mode** it takes an exclusive grab (`EVIOCGRAB`) on the pad. The grab
applies to the whole input device, so `js0`/joydev goes quiet too and nothing
leaks through to anything else.

In **game mode** it releases the grab and the pad behaves exactly as it did
before. It keeps reading the pad non-exclusively so the Legion-button override
still works from inside a game.

## Default mapping

| Control | Desktop action |
|---|---|
| **Left stick** | Move the cursor |
| **Right stick** | Nothing by default — see below |
| **D-pad** | Arrow keys |
| **A** | Left click |
| **B** | Right click |
| **X** | Toggle the on-screen keyboard (`wvkbd`) |
| **Y** | Enter |
| **RT** | Open the Window menu |
| **LT** | Escape |
| **LB / RB** | Previous / next workspace |
| **L3** (left stick click) | Middle click |
| **R3** (right stick click) | Hold for precision — cursor at 30% speed |
| **Start** | Open the Omarchy menu |
| **Select** | Super (Omarchy overview) |
| **Legion** | Hold ~0.6 s to force desktop/game mode |

Change any of it with `legion-config` (see below) rather than editing TOML.

A and B are the two mouse buttons, which is what you reach for most of the time.
Y is Enter for the keyboard-style half of the layout: walk a menu with the D-pad,
confirm with Y, back out with LT.

`RT` and `LT` here are the **triggers** (middle finger); `RB`/`LB` are the
**bumpers** above them (index finger); `L3`/`R3` are the **stick clicks**.

## The Window menu

RT opens a menu of window and workspace actions, navigable entirely from the pad
— D-pad to move, **Y** to choose, **LT** to back out, RT again to close.

| | |
|---|---|
| Close window | Fullscreen |
| Float / tile | Next / previous workspace |
| Send to next / previous workspace | On-screen keyboard |
| Gamepad off (game mode) | Lock |
| Power | |

It is a normal Omarchy menu route, so `omarchy menu summon window` opens it from
anywhere and it is searchable from the root menu. The rows are defined in
`omarchy/menu-window.jsonc` and installed into
`~/.config/omarchy/extensions/omarchy-menu.jsonc` between `legion-nav` markers.
Add or reorder rows there, then run `omarchy menu refresh`.

A menu beats a hold-a-modifier chord here: nothing to memorise, it is
self-documenting, and adding an action is one line rather than a spare button.

Key repeat on the D-pad comes from Hyprland's own `repeat_delay` / `repeat_rate`,
so held arrows repeat at whatever you have configured in `~/.config/hypr/input.lua`.

## Install

```bash
git clone <this repo> ~/Projects/omarchy/legion-go-s
cd ~/Projects/omarchy/legion-go-s
./install.sh
```

`install.sh` is idempotent — re-run it any time. It will:

1. check for `python-evdev`, `hyprctl` and `wvkbd`;
2. install `/etc/udev/rules.d/99-uinput.rules` (**the only step that needs sudo**)
   and reload udev;
3. symlink `bin/legion-nav` and `bin/legion-osk` into `~/.local/bin`;
4. copy the default config to `~/.config/legion-nav/config.toml` (never
   overwriting an existing one);
5. append a marked block to `~/.config/hypr/bindings.lua` and
   `~/.config/hypr/input.lua`, then validate with `hyprctl configerrors`;
6. enable and start `legion-nav.service` as a user service.

Undo all of it with `./uninstall.sh`.

### Why the udev rule is needed

Arch ships `/dev/uinput` as `root:root 0600` and provides no rule of its own, so
nothing in userspace can create virtual input devices. The rule hands it to the
`input` group, which you are already in. This is the same permission any
userspace remapper needs (ydotool, InputPlumber, sc-controller).

## Configuring it

```bash
legion-config          # the UI
legion-config --print   # the mapping as plain text
```

`legion-config` draws the device, shows what every control does, and lets you
change bindings and feel. **Changes apply to the running daemon as you make
them** and are only written to disk when you save — so cursor speed, deadzones
and the scroll engage delay can be tuned by feel instead of by guesswork.

It is drivable **from the gamepad itself**: the D-pad sends arrows, Y sends
Enter, LT sends Escape, and while it is open the daemon suppresses everything
else so the bumpers cannot switch workspace out from under you. So you can
reconfigure the handheld while holding it, with no keyboard attached.

- **↑/↓** move, **←/→** switch tab or adjust a value
- **⏎** change a binding or toggle a setting, **esc** backs out
- **↓** past the end of the list reaches **Save · Revert · Quit**
- Saving backs the file up first, and preserves every comment in it

```

       LB                          RB     
       LT                          RT     
     ╭────────────────────────────────╮   
     │  ▲             Y               │   
     │ ◄ ►           X   B            │   
     │  ▼             A               │   
     │ L3       SEL  LGN  STA      R3 │   
     ╰────────────────────────────────╯   

  A                       Left click
  B                       Right click
  X                       On-screen keyboard
  Y                       Enter
  LB                      Workspace previous
  RB                      Workspace next
  LT                      Escape
  RT                      Window menu
  L3 (left stick click)   Middle click
  R3 (right stick click)  Precision (hold)
  Start                   Omarchy menu
  Select                  Super (overview)
  Legion                  Desktop/game toggle (hold)
  D-pad up                Arrow up
  D-pad down              Arrow down
  D-pad left              Arrow left
  D-pad right             Arrow right

  Cursor  1500 px/s   deadzone 12%   curve 2   precision 30%
  Scroll  off   deadzone 35%   engage 150 ms   18 notch/s
```

Reading the config from a script:

```bash
legion-nav config          # effective config as JSON (defaults + your overrides)
```

That is deliberately the only "state" API — `~/.config/legion-nav/config.toml`
stays the single source of truth rather than being mirrored somewhere that can
drift out of date.

## Usage

```bash
legion-nav status     # current mode, as JSON
legion-nav toggle     # flip between desktop and game mode
legion-nav on         # force desktop mode
legion-nav off        # force game mode
legion-nav auto       # drop the override, go back to automatic
legion-nav probe      # print every control you press, with its code
```

`SUPER + SHIFT + G` is bound to `legion-nav toggle`.

Logs: `journalctl --user -u legion-nav -f`

## Automatic mode switching

On every focus change `legion-nav` asks Hyprland what is focused and picks a
mode. A window counts as a game when any of these is true:

- its class matches `modes.game_classes` (glob patterns, case-insensitive);
- it sets the Wayland content-type hint to `game`;
- it is genuinely fullscreen and its class is not in `modes.desktop_classes`.

The fullscreen rule is the one that catches games you have not listed. If it
misfires — a fullscreen video player, say — add that class to `desktop_classes`,
or just hold the Legion button.

A manual override lasts until you toggle again or focus moves to a different
window class, so it never silently sticks.

## Tuning

Edit `~/.config/legion-nav/config.toml`, then:

```bash
systemctl --user restart legion-nav
```

The knobs you are most likely to want:

- **`cursor.max_speed`** — pixels per second at full deflection. The panel runs
  at scale 2, so the logical desktop is 960 px wide.
- **`cursor.expo`** — response curve. `1.0` is linear; higher gives finer control
  near centre without lowering the top speed.
- **`cursor.deadzone`** — the hardware only reports a 0.4% flat zone, which is far
  too tight to rest a thumb on. Default is 12%.
- **`scroll.natural`** — flip the scroll direction.
- **`triggers.press_at` / `release_at`** — the triggers are analog only (0–255,
  no digital press), so they are thresholded with hysteresis.

Actions take four forms:

```toml
a      = "key:KEY_ENTER"                      # hold a key while held
x      = "btn:BTN_LEFT"                       # hold a mouse button
start  = "exec:omarchy-menu"                  # run a command once, on press
r3     = "special:precision"                  # precision | mode_hold
select = "none"                               # nothing
```

Any `KEY_*` / `BTN_*` name from `python3 -c "from evdev import ecodes; print(ecodes.keys)"`
works.

## A note on the face buttons

Codes 307 and 308 have two sets of names that mean opposite things.
`Documentation/input/gamepad.rst` names the face buttons by compass point
(`BTN_NORTH` = 307, `BTN_WEST` = 308, which would make 307 the **Y** button on
an Xbox-style pad). The older joystick names put them the other way round
(`BTN_X` = 307, `BTN_Y` = 308). `python-evdev` prints both aliases for the same
code, so reading a capability dump tells you nothing.

**Verified on real hardware: `hid-lenovo-go-s` follows the legacy naming.** On
this pad 307 is the button printed **X** and 308 is the one printed **Y**, and
`legion-nav` is mapped to match the plastic.

If you are on different firmware, run `legion-nav probe`, press X and Y, and
check the reported name against the label. If they disagree, swap the `"x"` and
`"y"` entries in the `BUTTONS` table in `bin/legion-nav`.

## Testing

```bash
for t in tests/test_*.py; do python3 "$t" || break; done
```

| Suite | Covers |
|---|---|
| `test_mapping.py` | Mapping, curves, trigger hysteresis, mode switching, game detection — against a fake pad and stubbed uinput |
| `test_config_writer.py` | Surgical TOML editing: one line changes, comments and alignment survive, no table is ever dropped |
| `test_diagram.py` | Diagram geometry and that every highlight span points at its own label |
| `test_tui.py` | Drives `legion-config` in a real pty at several terminal sizes, including an edit-and-save round trip |

No hardware needed for any of them.

## How this fits the rest of the system

- The pad works at all because of the in-kernel **`hid_lenovo_go_s`** driver
  (stock Arch). Nothing else is in the path.
- **`hhd`** (Handheld Daemon) is installed on this machine but disabled and
  broken — it crashes looking for a keyboard HID child that `hid-lenovo-go-s`
  does not expose. `legion-nav` does not use it. **Do not enable `hhd@$USER`
  while `legion-nav` is running**: both want the pad, and they will fight.
- **`keyd`** is running but `/etc/keyd/default.conf` already excludes
  `1a86:e310`, so there is no conflict.

## Why the right stick does nothing

**Picking the machine up scrolled the page.** It really did, and it looks for all
the world like a motion sensor — but there is no gyroscope and no accelerometer
on this machine, and `legion-nav` only ever reads eight axes off one device.

The cause is simpler: **a thumbstick has mass.** Lifting the device off a table,
or just gripping it firmly, deflects the right stick — measured at close to
*full* deflection, not a slight nudge. The stick is, in effect, an accelerometer.

No deadzone alone fixes that, so right-stick scrolling ships **off**. Set
`enabled = true` under `[scroll]` to get it back, and two safeguards apply:

- `deadzone = 0.35` — far larger than the cursor's.
- `engage_ms = 150` — the stick must be *held* past the deadzone this long
  before scrolling starts. An inertial knock is over in tens of milliseconds; a
  deliberate scroll is not. Returning to centre re-arms it.

Diagnosed with `tools/inputcapture.py`, which is worth keeping for any
"what just did that?" input mystery.

## Identifying an unknown input

To identify it, bisect in two runs. `tools/inputcapture.py` opens **every**
input device and logs everything, and samples the gamepad axes separately so the
sticks are visible even while `legion-nav` holds its exclusive grab.

```bash
# 1. Rule legion-nav in or out. Stops it for the capture, then restarts it.
python3 tools/inputcapture.py --stop-daemon --seconds 20

# 2. If it still happens with the daemon stopped, legion-nav is innocent --
#    the summary names whatever did it.
python3 tools/inputcapture.py --seconds 20
```

Rotate the device while it runs. The summary counts every event by device, gives
the peak stick deflection against the 20% scroll deadzone, and says outright
whether the touchscreen was touched and whether any wheel event existed.

`tools/scrollwatch.py` is the lighter version: it only watches wheel and touch
events, live, without stopping anything.

The touchscreen is the usual answer. A touch-drag scrolls in most apps, and that
scroll is synthesised by the application from touch events, so no wheel event
exists anywhere to trace. Gripping the device near the panel while moving it is
enough. If that is what is happening, the fix is not in `legion-nav` at all:

```lua
-- ~/.config/hypr/input.lua — ignore the built-in touchscreen entirely
hl.config({ device = { { name = "nvtk0603:00-0603:f200", enabled = false } } })
```

## Limitations

- **Back paddles, Legion-R and the QAM button are not reachable.** They are not
  on the evdev node at all — they live on the other hidraw interfaces, which is
  what `hhd` would have read. `BTN_MODE` (the Legion button) is the only system
  key available.
- **No gyro, and none to have.** This machine exposes no accelerometer or
  gyroscope at all — not on the pad's evdev node, and not as an IIO device.
- Automatic detection needs Hyprland IPC. Without it the daemon stays in desktop
  mode and reconnects when Hyprland comes back.
