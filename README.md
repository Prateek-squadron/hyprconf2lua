# hyprconf2lua

**Your `hyprland.conf` is going away. Here's the one-liner to migrate.**

Hyprland 0.55+ replaced the old hyprlang config with Lua. The old format will be dropped in a future release. **hyprconf2lua** converts your existing config automatically — no manual rewrite needed.

```bash
pip install hyprconf2lua
hyprconf2lua ~/.config/hypr/hyprland.conf -o hyprland.lua
```

That's it. ~97% of your config converts cleanly. The rest gets flagged with `-- TODO` comments telling you exactly what to touch up.

> **PEP 668 ("externally managed environment")?** Use the clone method instead — zero pip needed:
> `git clone https://github.com/Prateek-squadron/hyprconf2lua.git && cd hyprconf2lua && ./install.sh`

---

## What it looks like

**Before** (old `hyprland.conf`):
```ini
$mainMod = SUPER

general {
    gaps_in = 5
    gaps_out = 20
}

bind = $mainMod, Q, exec, kitty
bind = $mainMod, F, fullscreen

windowrule = float, ^(pavucontrol)$

exec-once = waybar
exec-once = mako
```

**After** (new `hyprland.lua`):
```lua
local mainMod = "SUPER"

hl.config({
    general = {
        gaps_in = 5,
        gaps_out = 20,
    },
})

hl.bind(mainMod .. " + " .. "Q", hl.dsp.exec_cmd("kitty"))
hl.bind(mainMod .. " + " .. "F", hl.dsp.window.fullscreen())

hl.window_rule({
    name  = "float",
    match = { class = "^(pavucontrol)$" },
    float = true,
})

hl.on("hyprland.start", function()
    hl.exec_cmd("waybar")
    hl.exec_cmd("mako")
end)
```

---

## Installation

### pip install (recommended)

```bash
pip install hyprconf2lua           # or: pip install --user hyprconf2lua
hyprconf2lua ~/.config/hypr/hyprland.conf -o hyprland.lua
```

### pipx install

```bash
pipx install hyprconf2lua          # isolated, no PEP 668 issues
```

### Clone + install (no pip, works everywhere)

```bash
git clone https://github.com/Prateek-squadron/hyprconf2lua.git
cd hyprconf2lua
./install.sh                       # symlinks to ~/.local/bin
```

### One-shot (no install at all)

```bash
git clone https://github.com/Prateek-squadron/hyprconf2lua.git
cd hyprconf2lua
PYTHONPATH=src python3 -m hyprconf2lua ~/.config/hypr/hyprland.conf > hyprland.lua
```

---

## Full migration guide

1. **Backup** your current config:
   ```bash
   cp -r ~/.config/hypr ~/.config/hypr.bak
   ```

2. **Convert your main config**:
   ```bash
   hyprconf2lua ~/.config/hypr/hyprland.conf -o ~/.config/hypr/hyprland.lua
   ```

3. **Check for flags** — run with `--check` to find anything that needs manual review:
   ```bash
   hyprconf2lua --check ~/.config/hypr/hyprland.conf
   # exits 0 if clean, 3 if anything flagged
   ```

4. **Convert sourced files** — if your config has `source = somefile.conf`, convert those too:
   ```bash
   hyprconf2lua --dir ~/.config/hypr --in-place
   ```
   This converts every `.conf` in the directory to `.lua`.

5. **Review `-- TODO` markers** — search for these in the generated `.lua` files and handle them manually.

6. **Test** — restart Hyprland and make sure everything works:
   ```bash
   hyprctl reload
   ```

---

## What works

| Category | Status |
|----------|--------|
| Keybinds (`bind`, `bindl`, `bindr`, `bindm`, `binde`, `bindd`, etc.) | ✅ All flags and combined forms |
| Monitors | ✅ 100% |
| Window rules (`windowrule`, `windowrulev2`) | ✅ Regex patterns, opacity, all rule types |
| Autostart (`exec-once`, `exec`, `exec-shutdown`) | ✅ Preserves spaces, `&`, pipes |
| Environment (`env`) | ✅ Commas in values preserved |
| Animations and beziers | ✅ Named curves, animation presets |
| Device sections (`device:name { }`) | ✅ |
| Gestures | ✅ |
| Workspace rules | ✅ default, monitor, gaps, etc. |
| Layer rules | ✅ blur, ignorealpha, noanim |
| Submap blocks (`submap = name` … `submap = reset`) | ✅ `hl.define_submap()` |
| Config sections (`general`, `decoration`, `input`, …) | ✅ Includes nested subsections (shadow, blur, touchpad) |
| Variables (`$var = value`) | ✅ Resolved in binds and execs |
| Comments (`#`) | ✅ Preserved as `--` |
| `plugin { }` | ⚠️ Flagged with TODO — plugin APIs are plugin-specific |
| `source = *.conf` | ⚠️ Flagged with conversion reminder |
| `$` glob patterns in sources | ⚠️ Needs manual handling |

**Coverage:** ~97% on standard configs, 90%+ on complex setups like Omarchy, **0% false positives** — everything flagged genuinely needs attention.

---

## Why this over the Go tool?

There's another converter (`hyprlang2lua` by EIonTusk) written in Go. Here's why this one exists:

- **No compile step** — Go binaries need to be downloaded or compiled. This is `pip install` (or just `python3 -m`) and done. Arch ships Python, you already have it.
- **Easier to contribute** — Python has a lower barrier. If your config hits an edge case, you or someone else can fix it in minutes without learning Go.
- **Better coverage** — Handles Omarchy's `bindd` with description labels, nested config sections (shadow/blur inside decoration), combined bind flags (`bindle`, `bindm`), mouse binds, commas inside env values, and submap blocks. The Go tool is more basic.
- **CI-friendly** — `--check` mode exits 3 if anything needs review. Great for git hooks and automated pipelines.

---

## Usage reference

```bash
# Convert a single file to stdout
hyprconf2lua hyprland.conf > hyprland.lua

# Convert and write to file
hyprconf2lua hyprland.conf -o hyprland.lua

# Convert from stdin
cat hyprland.conf | hyprconf2lua > hyprland.lua

# Convert all .conf files in a directory tree
hyprconf2lua --dir ~/.config/hypr --in-place

# Check mode (CI): exits 3 if anything needs manual review
hyprconf2lua --check hyprland.conf

# Show translation statistics
hyprconf2lua hyprland.conf --report

# Print version
hyprconf2lua --version
```

If you didn't install via `./install.sh`, prefix commands with `PYTHONPATH=src python3 -m`:
```bash
cd hyprconf2lua
PYTHONPATH=src python3 -m hyprconf2lua ~/.config/hypr/hyprland.conf -o ~/.config/hypr/hyprland.lua
```

---

## Manual review checklist

After conversion, search your `.lua` files for `TODO`:

- **`plugin { }`** — these need `hl.plugin.*` APIs specific to each plugin. See your plugin docs.
- **`source = path`** — each sourced `.conf` needs individual conversion. Run `hyprconf2lua` on each one.
- **`submap` bindings** — now handled automatically with `hl.define_submap()`.
- **Unknown dispatchers** — rare or custom dispatchers are flagged. Check the [Hyprland wiki](https://wiki.hyprland.org) for the Lua equivalent.

---

## Project

- **GitHub:** [github.com/Prateek-squadron/hyprconf2lua](https://github.com/Prateek-squadron/hyprconf2lua)
- **License:** MIT
- **Contributions welcome** — Python, simple codebase, ~400 lines of core logic. If your config doesn't convert cleanly, open an issue or send a PR.

---

*Made because Hyprland 0.55 broke everyone's config and someone had to write the migration tool.*
