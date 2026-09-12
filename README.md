# Legion Go Navigation for Omarchy

Drive the Omarchy desktop with the built-in gamepad of a **Lenovo Legion Go S**
(83L3). The left stick is the mouse, the D-pad is the arrow keys and A selects.
When a game takes focus, it gets out of the way automatically.

Built for Arch and Hyprland (Wayland). No Steam, no gamescope and no Handheld
Daemon required.

```
       LB                              RB
       LT                              RT
     ╭────────────────────────────────────╮
     │  ▲                             Y   │
     │ ◄ ►                    STA   X   B │
     │  ▼                             A   │
     │  L3                         R3     │
     ╰────────────────────────────────────╯
```

---

## What it does

`legion-nav` is a small user service that reads the pad directly from evdev and
re-emits it as a virtual mouse and keyboard through `uinput`. It runs in one of
two modes:

- **Desktop mode.** It takes an exclusive grab (`EVIOCGRAB`) on the pad. The
  grab applies to the whole input device, so `js0`/joydev goes quiet too and
  nothing leaks through to anything else.
- **Game mode.** It releases the grab and the pad behaves exactly as it did
  before. It keeps reading the pad non-exclusively, so the Legion button can
  still switch modes from inside a game.

It switches between them on its own as focus changes (see
[Automatic mode switching](#automatic-mode-switching)).

### Default mapping

| Control | Desktop action |
|---|---|
| **Left stick** | Move the cursor |
| **Right stick** | Scroll, on a held push rather than a nudge ([why](#why-scrolling-needs-a-held-push)) |
| **D-pad** | Arrow keys |
| **A** | Left click |
| **B** | Right click |
| **X** | Toggle the on-screen keyboard (`wvkbd`) |
| **Y** | Enter |
| **RT** | Open the [Window menu](#the-window-menu) |
| **LT** | Escape |
| **LB / RB** | Previous / next workspace |
| **L3** (left stick click) | Middle click |
| **R3** (right stick click) | Hold for precision, cursor at 30% speed |
| **Start** | Open the Omarchy menu |
| **Select** | *unbound* |
| **Legion** | Hold ~0.6 s to force desktop or game mode |

A and B are the two mouse buttons, which is what you reach for most of the time.
The rest is laid out like a keyboard: walk a menu with the D-pad, confirm with Y,
back out with LT.

`RT` and `LT` are the **triggers** (middle finger), `RB` and `LB` are the
**bumpers** above them (index finger), and `L3` and `R3` are the **stick clicks**.

## Install

```bash
git clone https://github.com/mtmr0x/omarchy-legion-go-s.git ~/Projects/omarchy/legion-go-s
cd ~/Projects/omarchy/legion-go-s
./install.sh
```

You need to be in the `input` group, and `python-evdev`, `hyprland` and `wvkbd`
must be installed. The installer tells you the exact `omarchy pkg add` command
if anything is missing.

`install.sh` is idempotent, so re-run it any time. It will:

1. check the dependencies and your `input` group membership;
2. install `/etc/udev/rules.d/99-uinput.rules` and reload udev (**the only step
   that needs sudo**, see below);
3. symlink `legion-nav`, `legion-osk` and `legion-config` into `~/.local/bin`;
4. copy the default config to `~/.config/legion-nav/config.toml`, never
   overwriting an existing one;
5. append marked blocks to `~/.config/hypr/bindings.lua` (`SUPER + SHIFT + G`
   toggles the pad) and `~/.config/hypr/input.lua` (keeps the virtual pointer at
   1:1), then validate with `hyprctl configerrors`;
6. add the Window menu to `~/.config/omarchy/extensions/omarchy-menu.jsonc`;
7. enable and start `legion-nav.service` as a user service;
8. offer to open the configurator. Pass `--no-config` to skip it.

Undo all of it with `./uninstall.sh`. It leaves your
`~/.config/legion-nav/` tuning and the udev rule in place, and prints how to
remove them.

### Why the udev rule is needed

Arch ships `/dev/uinput` as `root:root 0600` and provides no rule of its own, so
nothing in userspace can create virtual input devices. The rule hands it to the
`input` group. This is the same permission any userspace remapper needs
(ydotool, InputPlumber, sc-controller).

## Configure

```bash
legion-config           # the configurator
legion-config --print   # the diagram and mapping as plain text
```

`legion-config` draws the device, shows what every control does, and lets you
change bindings and feel. **Changes apply to the running daemon as you make
them** and are only written to disk when you save, so cursor speed, deadzones
and the scroll delay can be tuned by feel instead of by guesswork.

It is drivable **from the gamepad itself**. While it is open the daemon passes
through only the D-pad, Y and LT, so the bumpers cannot switch workspace out
from under you and you can reconfigure the handheld with no keyboard attached.

- **↑ / ↓** move, **← / →** switch tab or adjust a value
- **⏎** change a binding or toggle a setting, **esc** backs out
- **↓** past the end of the list reaches **Save · Revert · Quit**
- Saving backs the file up first and preserves every comment in it

The **Buttons** tab lists every control against its action:

```
 legion-nav · configure                                          saved

                   LB                              RB
                   LT                              RT
                 ╭────────────────────────────────────╮
                 │  ▲                             Y   │
                 │ ◄ ►                    STA   X   B │
                 │  ▼                             A   │
                 │  L3                         R3     │
                 ╰────────────────────────────────────╯

   Buttons   Feel
  A                        Left click
  B                        Right click
  X                        On-screen keyboard
  Y                        Enter
  LB                       Workspace previous
  RB                       Workspace next
  LT                       Escape
  RT                       Window menu
  L3 (left stick click)    Middle click
  R3 (right stick click)   Precision (hold)
  Start                    Omarchy menu
  Select                   Nothing
  Legion                   Desktop/game toggle (hold)
  D-pad up                 Arrow up
  D-pad down               Arrow down
  D-pad left               Arrow left

   Save   Revert   Quit
  ↑↓ move   ⏎ change   esc back   ↓ past the end for Save
```

Pressing ⏎ on a control opens the action picker. `Custom…` takes any action
spec (see [Editing the file](#editing-the-file)):

```
┌─ RT ───────────────────────────────────────┐
│                                            │
│   Arrow up                                 │
│   Arrow down                               │
│   Arrow left                               │
│   Arrow right                              │
│   Page up                                  │
│   Page down                                │
│   Home                                     │
│   End                                      │
│   Delete                                   │
│   Super (overview)                         │
│   Alt                                      │
│   Ctrl                                     │
│   Shift                                    │
│   On-screen keyboard                       │
│ • Window menu                              │
│   Omarchy menu                             │
│   Workspace previous                       │
│   Workspace next                           │
│   Close window                             │
│   Fullscreen                               │
│   Float / tile                             │
│   Lock screen                              │
│   Precision (hold)                         │
│   Desktop/game toggle (hold)               │
│   Nothing                                  │
│   Custom…                                  │
│                                            │
└─ ⏎ choose · esc cancel ────────────────────┘
```

The **Feel** tab holds the analog tuning, adjusted with ← and →:

```
   Buttons   Feel
  Cursor speed             ▮▮▮▯▯▯▯▯▯▯  1500 px/s
  Cursor deadzone          ▮▮▯▯▯▯▯▯▯▯  12%
  Cursor curve             ▮▮▮▯▯▯▯▯▯▯  2
  Precision factor         ▮▮▮▯▯▯▯▯▯▯  30%
  Polling rate             ▮▮▮▮▮▮▮▯▯▯  200 Hz
  Scroll enabled             [on]   on
  Scroll deadzone          ▮▮▮▮▯▯▯▯▯▯  35%
  Scroll engage delay      ▮▮▯▯▯▯▯▯▯▯  150 ms
  Scroll speed             ▮▮▮▯▯▯▯▯▯▯  18 notch/s
  Natural scroll            [off]   off
  Trigger press at         ▮▮▮▮▮▯▯▯▯▯  50%
  Trigger release at       ▮▮▮▮▯▯▯▯▯▯  35%
  Legion hold time         ▮▮▯▯▯▯▯▯▯▯  0.6 s

   Save   Revert   Quit
  ↑↓ move   ←→ adjust   ⏎ toggle   esc back   ↓ for Save
```

A few of these deserve context:

- **Cursor speed** is pixels per second at full deflection. The panel runs at
  scale 2, so the logical desktop is 960 px wide.
- **Cursor curve** is the response curve. `1` is linear, and higher gives finer
  control near centre without lowering the top speed.
- **Cursor deadzone** defaults to 12% because the hardware only reports a 0.4%
  flat zone, which is far too tight to rest a thumb on.
- **Trigger press/release** exist because the triggers are analog only (0 to
  255, no digital press), so they are thresholded with hysteresis.

### Editing the file

Everything the configurator does is stored in `~/.config/legion-nav/config.toml`,
which is commented throughout. If you edit it by hand, apply it with
`systemctl --user restart legion-nav`.

Actions take five forms:

```toml
y      = "key:KEY_ENTER"                      # hold a key while held
a      = "btn:BTN_LEFT"                       # hold a mouse button
start  = "exec:omarchy-menu"                  # run a command once, on press
r3     = "special:precision"                  # precision | mode_hold
select = "none"                               # nothing
```

Any `KEY_*` / `BTN_*` name from `python3 -c "from evdev import ecodes; print(ecodes.keys)"`
works. `exec:` commands run through a shell, so Hyprland dispatchers use the Lua
syntax, for example `exec:hyprctl dispatch 'hl.dsp.window.close()'`.

To read the config from a script:

```bash
legion-nav config       # effective config as JSON (defaults + your overrides)
```

That is deliberately the only "state" API. The TOML file stays the single source
of truth rather than being mirrored somewhere that can drift out of date.

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

## The Window menu

RT opens a menu of window and workspace actions, navigable entirely from the
pad. Press RT again to close it.

| | |
|---|---|
| Close window | Fullscreen |
| Float / tile | Next / previous workspace |
| Send to next / previous workspace | On-screen keyboard |
| Gamepad off (game mode) | Configure gamepad |
| Lock | Power |

It is a normal Omarchy menu route, so `omarchy menu summon window` opens it from
anywhere and it is searchable from the root menu. The rows are defined in
`omarchy/menu-window.jsonc` and installed between `legion-nav` markers. Add or
reorder rows in `~/.config/omarchy/extensions/omarchy-menu.jsonc`, then run
`omarchy menu refresh`.

A menu beats a hold-a-modifier chord here. There is nothing to memorise, it is
self-documenting, and adding an action is one line rather than a spare button.

Key repeat on the D-pad comes from Hyprland's own `repeat_delay` and
`repeat_rate`, so held arrows repeat at whatever you have set in
`~/.config/hypr/input.lua`.

## Automatic mode switching

On every focus change `legion-nav` asks Hyprland what is focused and picks a
mode. A window counts as a game when any of these is true:

- its class matches `modes.game_classes` (glob patterns, case-insensitive);
- it sets the Wayland content-type hint to `game`;
- it is genuinely fullscreen and its class is not in `modes.desktop_classes`.

The fullscreen rule is the one that catches games you have not listed. If it
misfires, on a fullscreen video player for example, add that class to
`desktop_classes`, hold the Legion button, or use `SUPER + SHIFT + G`.

A manual override lasts until you toggle again or focus moves to a different
window class, so it never silently sticks.

Detection needs Hyprland IPC. Without it the daemon stays in desktop mode and
reconnects when Hyprland comes back.

## Why scrolling needs a held push

**Picking the machine up scrolled the page.** It looks for all the world like a
motion sensor, but there is no gyroscope and no accelerometer on this machine,
and `legion-nav` only ever reads eight axes off one device.

The cause is simpler: **a thumbstick has mass.** Lifting the device off a table,
or just gripping it firmly, deflects the right stick, measured at close to
*full* deflection rather than a slight nudge. The stick is, in effect, an
accelerometer.

A deadzone alone cannot fix that, so scrolling is gated on **time** instead:

- **Scroll engage delay** (`engage_ms = 150`): the stick must be *held* past the
  deadzone this long before scrolling starts. An inertial knock is over in tens
  of milliseconds, a deliberate scroll is not. Returning to centre re-arms it.
- **Scroll deadzone** (`deadzone = 0.35`): far larger than the cursor's, as a
  second layer.

You will feel a brief pause before a scroll begins, which is the delay doing its
job. Raise the delay if a knock still gets through, lower it if the pause annoys,
or turn **Scroll enabled** off to silence the right stick completely.

### Identifying an unknown input

If something still moves that you did not ask to move, bisect it in two runs.
`tools/inputcapture.py` opens **every** input device and logs everything, and
samples the gamepad axes separately so the sticks are visible even while
`legion-nav` holds its exclusive grab.

```bash
# 1. Rule legion-nav in or out. Stops it for the capture, then restarts it.
python3 tools/inputcapture.py --stop-daemon --seconds 20

# 2. If it still happens with the daemon stopped, legion-nav is innocent.
#    The summary names whatever did it.
python3 tools/inputcapture.py --seconds 20
```

Move the device while it runs. The summary counts every event by device, gives
the peak stick deflection, and says outright whether the touchscreen was touched
and whether any wheel event existed.

`tools/scrollwatch.py` is the lighter version. It only watches wheel and touch
events, live, without stopping anything.

The touchscreen is the usual answer. A touch-drag scrolls in most apps, and that
scroll is synthesised by the application from touch events, so no wheel event
exists anywhere to trace. Gripping the device near the panel while moving it is
enough. If that is what is happening, the fix is not in `legion-nav` at all:

```lua
-- ~/.config/hypr/input.lua: ignore the built-in touchscreen entirely
hl.config({ device = { { name = "nvtk0603:00-0603:f200", enabled = false } } })
```

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

## How this fits the rest of the system

- The pad works at all because of the in-kernel **`hid_lenovo_go_s`** driver
  (stock Arch). Nothing else is in the path.
- **`hhd`** (Handheld Daemon) crashes on this machine looking for a keyboard HID
  child that `hid-lenovo-go-s` does not expose, and `legion-nav` does not use
  it. **Do not enable `hhd@$USER` while `legion-nav` is running**: both want the
  pad, and they will fight.
- **`keyd`**, if you run it, should exclude the pad (`1a86:e310`) in
  `/etc/keyd/default.conf` to avoid a conflict.

## Limitations

- **Back paddles, Legion-R and the QAM button are not reachable.** They are not
  on the evdev node at all. They live on the other hidraw interfaces, which is
  what `hhd` would have read. `BTN_MODE` (the Legion button) is the only system
  key available.
- **No gyro, and none to have.** This machine exposes no accelerometer or
  gyroscope at all, neither on the pad's evdev node nor as an IIO device.
- The **Select** and **Legion** buttons are bindable but not drawn on the
  diagram, because their physical location on this unit is unclear. Run
  `legion-nav probe` to see which, if either, your unit sends.

## Testing

```bash
for t in tests/test_*.py; do python3 "$t" || break; done
```

| Suite | Covers |
|---|---|
| `test_mapping.py` | Mapping, curves, trigger hysteresis, mode switching and game detection, against a fake pad and stubbed uinput |
| `test_config_writer.py` | Surgical TOML editing: one line changes, comments and alignment survive, no table is ever dropped |
| `test_diagram.py` | Diagram geometry, and that every highlight span points at its own label |
| `test_tui.py` | Drives `legion-config` in a real pty at several terminal sizes, including an edit-and-save round trip |

No hardware needed for any of them.
