#!/bin/bash
# Remove everything install.sh put on the system. The repo itself stays.
set -euo pipefail

BIN="$HOME/.local/bin"
UNITS="$HOME/.config/systemd/user"
HYPR="$HOME/.config/hypr"
RULE=/etc/udev/rules.d/99-uinput.rules

info() { printf '\033[1;34m::\033[0m %s\n' "$*"; }
ok()   { printf '\033[1;32m ok\033[0m %s\n' "$*"; }

info "Stopping the service"
systemctl --user disable --now legion-nav.service 2>/dev/null || true
rm -f "$UNITS/legion-nav.service"
systemctl --user daemon-reload
ok "service removed"

info "Removing binaries"
rm -f "$BIN/legion-nav" "$BIN/legion-osk" "$BIN/legion-config"
ok "symlinks removed"

info "Removing the Hyprland blocks"
for file in "$HYPR/bindings.lua" "$HYPR/input.lua"; do
  [[ -e "$file" ]] || continue
  if grep -qF -- "-- >>> legion-nav >>>" "$file"; then
    cp "$file" "$file.bak.$(date +%s)"
    sed -i '/-- >>> legion-nav >>>/,/-- <<< legion-nav <<</d' "$file"
    ok "cleaned $file (backup kept alongside)"
  fi
done
command -v hyprctl >/dev/null && hyprctl reload >/dev/null 2>&1 || true

info "Removing the Window menu"
MENU="$HOME/.config/omarchy/extensions/omarchy-menu.jsonc"
if [[ -e "$MENU" ]] && grep -qF -- "// >>> legion-nav >>>" "$MENU"; then
  cp "$MENU" "$MENU.bak.$(date +%s)"
  sed -i '/\/\/ >>> legion-nav >>>/,/\/\/ <<< legion-nav <<</d' "$MENU"
  omarchy menu refresh >/dev/null 2>&1 || true
  ok "cleaned $MENU (backup kept alongside)"
fi

echo
echo "Left in place on purpose:"
echo "  ~/.config/legion-nav/   your tuning -- delete it by hand if you want"
echo "  $RULE"
echo "      the /dev/uinput rule is generally useful. Remove it with:"
echo "      sudo rm $RULE && sudo udevadm control --reload"
