# hyprconf2lua

Convert Hyprland `hyprland.conf` (hyprlang) files to Lua config format (v0.55+).

Hyprland 0.55 (May 2026) introduced Lua-based configuration. The old hyprlang syntax will be removed in a future release. **hyprconf2lua** automates the migration.

## Features

- **All major directives** — config sections, binds, monitors, window rules, env vars, exec/autostart, animations, beziers, devices, gestures, workspace rules, layer rules
- **Variable resolution** — `$var` → `local var`, references resolved automatically
- **Bind flag support** — `bindl`, `bindr`, `bindn`, `bindm`, `binde`, `bindd`, `bindt`, `bindi`, `bindp`, plus combined forms like `bindle`
- **Omarchy compatibility** — handles `bindd` with description labels
- **Directory mode** — batch-convert all `.conf` files in a tree
- **Check mode** — CI-friendly: exit code 3 if any directive needs manual review
- **Comments preserved** — `#` → `--` in the same position
- **~97% coverage** on common configs; remaining edge cases flagged with `-- TODO` markers

## Install

```bash
# pip install (from source)
pip install .

# or directly
python -m hyprconf2lua hyprland.conf > hyprland.lua
```

## Usage

```bash
# Convert a single file → stdout
hyprconf2lua ~/.config/hypr/hyprland.conf > hyprland.lua

# Convert from stdin
cat hyprland.conf | hyprconf2lua > hyprland.lua

# Write to a specific output file
hyprconf2lua hyprland.conf -o hyprland.lua

# Convert an entire config directory
hyprconf2lua --dir ~/.config/hypr --in-place

# Check mode (CI): exit 3 if anything needs manual review
hyprconf2lua --check hyprland.conf

# Show translation statistics
hyprconf2lua hyprland.conf --report
```

## Supported Directives

| Category | Directives | Lua Output |
|----------|-----------|------------|
| **Config sections** | `general`, `decoration`, `input`, `animations`, `gestures`, `misc`, `binds`, `cursor`, `debug`, `dwindle`, `master`, `group`, `render`, `xwayland`, `opengl`, `ecosystem`, `experimental`, `layout`, `scrolling`, `quirks` | `hl.config({...})` |
| **Key bindings** | `bind`, `bindl`, `bindr`, `bindn`, `bindm`, `binde`, `bindo`, `bindt`, `bindi`, `bindp`, `bindc`, `bindd` + combined flags | `hl.bind(...)` |
| **Monitors** | `monitor` | `hl.monitor({...})` |
| **Window rules** | `windowrule`, `windowrulev2` | `hl.window_rule({...})` |
| **Autostart** | `exec-once`, `execr-once` | `hl.on("hyprland.start", ...)` |
| **Exec** | `exec` | `hl.on("config.reloaded", ...)` |
| **Environment** | `env` | `hl.env(...)` |
| **Animations** | `animation` | `hl.animation({...})` |
| **Beziers/Curves** | `bezier` | `hl.curve(...)` |
| **Devices** | `device:name { ... }` | `hl.device({name=..., ...})` |
| **Gestures** | `gesture { ... }` | `hl.gesture({...})` |
| **Workspace rules** | `workspace` | `hl.workspace_rule({...})` |
| **Layer rules** | `layerrule` | `hl.layer_rule({...})` |
| **Variables** | `$var = value` | `local var = value` |
| **Comments** | `# text` | `-- text` |
| **Source includes** | `source = path` | Flagged with conversion reminder |

### Dispatchers

Most Hyprland dispatchers are mapped automatically:

| Old | New Lua |
|-----|---------|
| `exec, cmd` | `hl.dsp.exec_cmd("cmd")` |
| `killactive` | `hl.dsp.window.close()` |
| `fullscreen` | `hl.dsp.window.fullscreen()` |
| `togglefloating` | `hl.dsp.window.float()` |
| `pseudo` | `hl.dsp.window.pseudo()` |
| `movefocus, l\|r\|u\|d` | `hl.dsp.focus({direction = "left\|..."})` |
| `workspace, n` | `hl.dsp.focus({workspace = n})` |
| `movetoworkspace, n` | `hl.dsp.window.move({workspace = n})` |
| `layoutmsg, msg` | `hl.dsp.layout("msg")` |
| `cyclenext` | `hl.dsp.window.cycle_next()` |
| `togglespecialworkspace, n` | `hl.dsp.workspace.toggle_special(n)` |
| `mouse, 272\|273` | `hl.dsp.window.drag()\|resize()` |
| `pin` | `hl.dsp.window.pin()` |
| `pass` | `hl.dsp.pass({...})` |
| `sendshortcut` | `hl.dsp.send_shortcut({...})` |
| `exit` | `hl.dsp.exit()` |

## Manual Review Needed

After conversion, check for these patterns:

- **submap = name** / **submap = reset** — these need to be wrapped in `hl.define_submap()`
- **plugin { ... }** — plugin configs have custom `hl.plugin.*` APIs
- **source = *** — sourced .conf files need individual conversion
- **Unknown dispatchers** — rare or custom dispatchers are flagged
- **Complex window rules** — rules like `opacity 0.8 0.8` need manual mapping

Run `hyprconf2lua --check` to find all flagged items.

## Coverage

Tested against:
- Stock Hyprland example config
- Omarchy default configs (bindings, monitors, envs, looknfeel, input, windows, autostart)
- Custom user configs with monitors, binds, window rules, animations, devices

## License

MIT
