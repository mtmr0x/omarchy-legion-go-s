#!/bin/bash
# Install legion-nav. Safe to re-run -- every step checks before it acts.
set -euo pipefail

RUN_CONFIG=1
for arg in "$@"; do
  case "$arg" in
    --no-config) RUN_CONFIG=0 ;;
    -h|--help)
      echo "usage: ./install.sh [--no-config]"
      echo "  --no-config   skip the interactive mapping editor at the end"
      exit 0 ;;
    *) echo "unknown option: $arg" >&2; exit 1 ;;
  esac
done

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN="$HOME/.local/bin"
CONFIG="$HOME/.config/legion-nav"
UNITS="$HOME/.config/systemd/user"
HYPR="$HOME/.config/hypr"
RULE=/etc/udev/rules.d/99-uinput.rules

BEGIN="-- >>> legion-nav >>>"
END="-- <<< legion-nav <<<"

info() { printf '\033[1;34m::\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m!!\033[0m %s\n' "$*"; }
ok()   { printf '\033[1;32m ok\033[0m %s\n' "$*"; }

# --------------------------------------------------------------- dependencies

info "Checking dependencies"
missing=()
python3 -c 'import evdev' 2>/dev/null || missing+=(python-evdev)
command -v hyprctl >/dev/null || missing+=(hyprland)
command -v wvkbd-mobintl >/dev/null || missing+=(wvkbd)
if ((${#missing[@]})); then
  warn "Missing: ${missing[*]}"
  echo "   Install them with: omarchy pkg add ${missing[*]}"
  exit 1
fi
ok "python-evdev, hyprctl, wvkbd present"

# --------------------------------------------------------------- /dev/uinput

if ! cmp -s "$REPO/udev/99-uinput.rules" "$RULE" 2>/dev/null; then
  info "Installing udev rule for /dev/uinput (needs sudo)"
  sudo install -m 644 "$REPO/udev/99-uinput.rules" "$RULE"
  sudo udevadm control --reload
  sudo udevadm trigger --subsystem-match=misc --sysname-match=uinput
  ok "$RULE installed"
else
  ok "udev rule already current"
fi

if ! id -nG | tr ' ' '\n' | grep -qx input; then
  warn "You are not in the 'input' group. Run:"
  echo "   sudo usermod -aG input $USER   # then log out and back in"
  exit 1
fi

# The rule only takes effect once the node is re-created or re-triggered.
if [[ -e /dev/uinput ]] && ! [[ -w /dev/uinput ]]; then
  warn "/dev/uinput is still not writable ($(stat -c '%U:%G %a' /dev/uinput))."
  echo "   A reboot will settle it if the udev trigger above did not."
else
  ok "/dev/uinput is writable"
fi

# --------------------------------------------------------------- binaries

info "Linking binaries into $BIN"
mkdir -p "$BIN"
for name in legion-nav legion-osk legion-config; do
  ln -sfn "$REPO/bin/$name" "$BIN/$name"
  ok "$BIN/$name -> $REPO/bin/$name"
done
case ":$PATH:" in
  *":$BIN:"*) ;;
  *) warn "$BIN is not on your PATH" ;;
esac

# --------------------------------------------------------------- config

mkdir -p "$CONFIG"
if [[ -e "$CONFIG/config.toml" ]]; then
  ok "$CONFIG/config.toml exists, leaving it alone"
else
  install -m 644 "$REPO/config/legion-nav.toml" "$CONFIG/config.toml"
  ok "$CONFIG/config.toml created"
fi

# --------------------------------------------------------------- hyprland

append_block() {
  local file="$1" body="$2"
  [[ -e "$file" ]] || { warn "$file does not exist, skipping"; return; }
  if grep -qF -- "$BEGIN" "$file"; then
    ok "$(basename "$file") already has the legion-nav block"
    return
  fi
  printf '\n%s\n%s\n%s\n' "$BEGIN" "$body" "$END" >> "$file"
  ok "appended legion-nav block to $file"
}

info "Wiring up Hyprland"
append_block "$HYPR/bindings.lua" \
'o.bind("SUPER + SHIFT + G", "Toggle gamepad navigation", "legion-nav toggle")'

append_block "$HYPR/input.lua" \
'-- Keep the virtual pointer at 1:1 so cursor speed is decided only by
-- ~/.config/legion-nav/config.toml, not by the global input sensitivity.
hl.config({
  device = {
    {
      name = "legion-nav-pointer",
      sensitivity = 0,
      accel_profile = "flat",
    },
  },
})'

if command -v hyprctl >/dev/null && hyprctl version >/dev/null 2>&1; then
  hyprctl reload >/dev/null
  errors="$(hyprctl configerrors 2>/dev/null || true)"
  if [[ -n "$errors" && "$errors" != "no errors" ]]; then
    warn "Hyprland reported config errors:"
    echo "$errors"
  else
    ok "Hyprland config reloaded cleanly"
  fi
fi

# --------------------------------------------------------------- omarchy menu

MENU="$HOME/.config/omarchy/extensions/omarchy-menu.jsonc"
info "Adding the Window menu (RT opens it)"
if [[ -e "$MENU" ]]; then
  python3 - "$MENU" "$REPO/omarchy/menu-window.jsonc" <<'PY'
import pathlib, shutil, sys, time

target = pathlib.Path(sys.argv[1])
block = pathlib.Path(sys.argv[2]).read_text().rstrip("\n")
BEGIN, END = "// >>> legion-nav >>>", "// <<< legion-nav <<<"

text = target.read_text()
if BEGIN in text and END in text:
    start = text.rindex("\n", 0, text.index(BEGIN)) + 1
    new = text[:start] + block + text[text.index(END) + len(END):]
else:
    close = text.rindex("}")          # insert just before the closing brace
    new = text[:close] + block + "\n" + text[close:]

if new != text:
    shutil.copy(target, f"{target}.bak.{int(time.time())}")
    target.write_text(new)
    print("  menu block written")
else:
    print("  menu block already current")
PY
  omarchy menu refresh >/dev/null 2>&1 || true
  ok "try it with: omarchy menu summon window"
else
  warn "$MENU not found, skipping the Window menu"
fi

# --------------------------------------------------------------- service

info "Installing the user service"
mkdir -p "$UNITS"
ln -sfn "$REPO/systemd/legion-nav.service" "$UNITS/legion-nav.service"
systemctl --user daemon-reload
systemctl --user enable --now legion-nav.service
sleep 1
if systemctl --user is-active --quiet legion-nav.service; then
  ok "legion-nav.service is running"
else
  warn "legion-nav.service did not start:"
  systemctl --user --no-pager status legion-nav.service | tail -20
  exit 1
fi

# --------------------------------------------------------------- configurator

if (( RUN_CONFIG )) && [[ -t 0 ]] && command -v gum >/dev/null; then
  echo
  # Omarchy themes gum through the environment; sourcing this keeps the prompt
  # in step with the current theme rather than whatever was set at login.
  source omarchy-restart-gum 2>/dev/null || true
  if gum confirm "Review the button mapping now?"; then
    "$REPO/bin/legion-config" || true
  fi
fi

echo
info "Done. Try it:"
echo "   legion-nav status          # what mode is it in"
echo "   legion-config              # see and change the mapping"
echo "   legion-nav probe           # check which button is which"
echo "   journalctl --user -u legion-nav -f"
echo
echo "   Left stick moves the cursor, right stick scrolls, D-pad is arrows."
echo "   A left-clicks, B right-clicks, X opens the keyboard, Y is Enter."
echo "   LT is Escape, RT opens the Window menu."
echo "   Hold the Legion button (or SUPER+SHIFT+G) to toggle desktop/game mode."
