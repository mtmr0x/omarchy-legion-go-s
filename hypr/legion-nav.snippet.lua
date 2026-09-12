-- legion-nav -- add these to your own Hyprland config.
--
-- install.sh appends them for you (marked with "legion-nav" comments) so you
-- can find and remove them later. Shown here for reference.

-- In ~/.config/hypr/bindings.lua -- toggle pad navigation without the pad:
o.bind("SUPER + SHIFT + G", "Toggle gamepad navigation", "legion-nav toggle")

-- In ~/.config/hypr/input.lua -- your global `sensitivity = 0.35` also scales
-- legion-nav's virtual pointer, which fights the speed tuning in
-- config/legion-nav.toml. This pins the virtual pointer to 1:1 so the only
-- place cursor speed is decided is legion-nav's own config.
hl.config({
  device = {
    {
      name = "legion-nav-pointer",
      sensitivity = 0,
      accel_profile = "flat",
    },
  },
})
