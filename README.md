# hyprconf2lua

<p align="center">
  <strong>Convert Hyprland legacy <code>.conf</code> (hyprlang) configurations to modern Lua format for Hyprland v0.55+</strong>
</p>

<p align="center">
  <a href="https://pypi.org/project/hyprconf2lua/"><img src="https://img.shields.io/pypi/v/hyprconf2lua.svg?color=blue" alt="PyPI version"></a>
  <a href="https://pepy.tech/projects/hyprconf2lua"><img src="https://static.pepy.tech/personalized-badge/hyprconf2lua?period=total&units=INTERNATIONAL_SYSTEM&left_color=BLACK&right_color=BLUE&left_text=downloads" alt="PyPI Downloads"></a>
  <a href="https://pypi.org/project/hyprconf2lua/"><img src="https://img.shields.io/pypi/pyversions/hyprconf2lua.svg" alt="Python versions"></a>
  <a href="https://github.com/Prateek-squadron/hyprconf2lua/blob/master/LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
  <a href="https://github.com/Prateek-squadron/hyprconf2lua/actions/workflows/ci.yml"><img src="https://github.com/Prateek-squadron/hyprconf2lua/actions/workflows/ci.yml/badge.svg" alt="CI status"></a>
</p>

<p align="center">
  🌐 <strong>Try it live online:</strong> <a href="https://prateek-squadron.github.io/hyprconf2lua/"><strong>prateek-squadron.github.io/hyprconf2lua</strong></a><br>
  <em>Runs 100% client-side via WebAssembly (Pyodide) — zero installation required, your config never leaves your browser.</em>
</p>

---

## Overview

Starting with **Hyprland v0.55+**, native Lua configuration scripting is officially supported via the `hl` Lua module. Configuring Hyprland with Lua brings powerful benefits: programmatic loop generation, structured tables, conditional monitor setup, dynamic workspace handling, and modular imports.

**`hyprconf2lua`** is a fast, zero-dependency AST transpiler that takes your existing `hyprland.conf` (and any sourced split files) and converts them into idiomatic, valid, and clean Lua configuration files.

Instead of unreliable regex search-and-replace, `hyprconf2lua` implements a full compiler pipeline:
```
hyprlang source (.conf)
      │
      ▼
   [ Lexer ]      (Regex tokenizer preserving string quoting & operators)
      │
      ▼
  [ Parser ]     (Recursive descent AST generation)
      │
      ▼
  [ Codegen ]    (Idiomatic Lua code generator for `hl` module)
      │
      ▼
 Lua config (.lua)
```

---

## Features

- **Bindings & Flags**: Transpiles `bind`, `bindd`, `binde`, `bindm`, `bindl`, `bindr`, `bindn`, `bindt`, `bindi`, `bindu`, `bindx`, `bindo`, `bindc`, `bindg`, etc. Correctly handles flags like `{ repeating = true }`, `{ non_consuming = true }`, `{ allow_input_capture = true }`, release triggers, and extracts `bindd` descriptions into `{ description = "..." }`.
- **Dispatcher Simplification**: Maps native dispatchers with correct type signatures and table arguments, and automatically rewrites legacy `exec, hyprctl dispatch X` into direct `hl.dsp.*` calls to prevent per-keypress process spawning.
- **Rules & Modern Directives**: Comprehensive support for `windowrule`, `windowrulev2`, `layerrule`, `workspace`, `permission`, and `monitorv2 { ... }` blocks with CSS gap tables (`reserved = { top, right, bottom, left }`).
- **Animations & Curves**: Directives like `animation =` and `bezier =` (including inside `animations {}` blocks) are converted into top-level `hl.animation()` and `hl.curve()` statements.
- **Variable Scoping & Expansion**: Converts Hyprland `$variables` into clean `local` Lua definitions and resolves scoped references.
- **Recursive Directory Walk**: Convert entire multi-file config directories (`--dir`) in one command. Missing `.lua` files are created safely without overwriting existing manual edits unless `--in-place` is specified.
- **Audit & Coverage Report**: Built-in `--report` mode categorizes directives into translated, passthrough, and flagged items, ensuring high conversion confidence.
- **CI / Validation Mode**: `--check` returns exit code `3` if any directive requires manual intervention.
- **Security Hardened**: Strict Lua string-escape validation, `os.getenv` injection protection, symlink write-target protection (`--dir` / `-o`), and bounded parser nesting depth (`MAX_BLOCK_DEPTH = 64`).
- **Zero Dependencies**: Pure Python with no third-party package dependencies.

---

## Installation

### Arch Linux (AUR)

```bash
# Using paru
paru -S hyprconf2lua

# Using yay
yay -S hyprconf2lua
```

### Via PyPI

```bash
# Using pip
pip install --upgrade hyprconf2lua

# Using pipx (isolated application)
pipx install hyprconf2lua
```

### From Source

```bash
git clone https://github.com/Prateek-squadron/hyprconf2lua.git
cd hyprconf2lua
pip install .
```

---

## Quick Start & Usage

### 1. Convert Single File

Convert your primary `hyprland.conf` to stdout or redirect to `hyprland.lua`:

```bash
# Redirect to file
hyprconf2lua ~/.config/hypr/hyprland.conf > ~/.config/hypr/hyprland.lua

# Or specify output with --out / -o
hyprconf2lua ~/.config/hypr/hyprland.conf -o ~/.config/hypr/hyprland.lua
```

### 2. Standard Input / Pipe

Pipe any configuration string directly into the converter:

```bash
cat ~/.config/hypr/hyprland.conf | hyprconf2lua > ~/.config/hypr/hyprland.lua
```

### 3. Convert an Entire Directory (Batch Mode)

If your Hyprland configuration is split into multiple `.conf` files (e.g., `keybinds.conf`, `rules.conf`, `monitors.conf`):

```bash
# Walks directory and writes a sibling .lua file next to each .conf
# (safely skips existing .lua files)
hyprconf2lua --dir ~/.config/hypr/

# Overwrite existing .lua files in the directory
hyprconf2lua --dir ~/.config/hypr/ --in-place
```

### 4. Audit & Coverage Reporting

Print a diagnostic breakdown of translated, passthrough, and manual review directives:

```bash
hyprconf2lua --report ~/.config/hypr/hyprland.conf > ~/.config/hypr/hyprland.lua
```
*Output to stderr:*
```text
Report: 84 translated, 0 passthrough, 0 flagged, 84 total, 100.0% coverage
```

### 5. Automated CI Check

Check whether a config translates cleanly without manual review warnings:

```bash
hyprconf2lua --check ~/.config/hypr/hyprland.conf
```
*Exits with code `0` if all directives translate cleanly, or `3` if any directive was flagged for manual review.*

---

## CLI Options Reference

| Flag | Argument | Description |
|------|----------|-------------|
| `-o`, `--out` | `<path>` | Path to output file (defaults to stdout) |
| `-d`, `--dir` | `<dir>` | Walk directory recursively, writing `.lua` next to each `.conf` |
| `--in-place` | None | When used with `--dir`, overwrite existing `.lua` sibling files |
| `--report` | None | Output translation statistics and coverage percentage to stderr |
| `--check` | None | Exit code 3 if any directive is flagged for manual review |
| `--version` | None | Display the version of `hyprconf2lua` |
| `-h`, `--help` | None | Display command help and exit |

---

## Conversion Example

### Legacy `hyprland.conf`
```ini
# General settings
general {
    gaps_in = 5
    gaps_out = 20
    border_size = 2
    col.active_border = rgba(33ccffee) rgba(00ff99ee) 45deg
    col.inactive_border = rgba(595959aa)
}

# Keybindings
bind = SUPER, Q, exec, kitty
bind = SUPER, C, killactive
bind = SUPER, M, exit
bind = SUPER, F, fullscreen, 1
binde = , XF86AudioRaiseVolume, exec, wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%+

# Window Rules
windowrulev2 = float, class:^(pavucontrol)$
windowrulev2 = size 700 600, class:^(pavucontrol)$
```

### Generated `hyprland.lua`
```lua
-- Generated by hyprconf2lua v1.8.2
-- https://github.com/Prateek-squadron/hyprconf2lua
-- Manual review may be needed for complex directives

---@module 'hl'

hl.config({
    general = {
        gaps_in = 5,
        gaps_out = 20,
        border_size = 2,
        col = {
            active_border = { colors = { "rgba(33ccffee)", "rgba(00ff99ee)" }, angle = 45 },
            inactive_border = "rgba(595959aa)",
        },
    },
})

hl.bind("SUPER + Q", hl.dsp.exec_cmd("kitty"))
hl.bind("SUPER + C", hl.dsp.window.kill_active())
hl.bind("SUPER + M", hl.dsp.exit())
hl.bind("SUPER + F", hl.dsp.window.fullscreen({ mode = 1 }))
hl.bind("XF86AudioRaiseVolume", hl.dsp.exec_cmd("wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%+"), { repeating = true })

hl.windowrule({
    match = {
        class = "pavucontrol",
    },
    float = true,
    size = { 700, 600 },
})
```

---

## Development & Testing

We maintain a comprehensive suite of unit and regression tests covering language syntax, edge-case escaping, variables, dispatchers, and rule combinations.

```bash
# Clone the repository
git clone https://github.com/Prateek-squadron/hyprconf2lua.git
cd hyprconf2lua

# Run pytest test suite
python -m pytest tests/

# Build wheel and source distributions
python -m build
```

---

## Contributing

Contributions, bug reports, and pull requests are warmly welcome! If you encounter any `.conf` directive or edge-case that doesn't translate as expected:

1. Open an issue on [GitHub Issues](https://github.com/Prateek-squadron/hyprconf2lua/issues) with the problematic `.conf` snippet.
2. Submit a pull request with a reproducible test case in `tests/test_converter.py`.

Special thanks to all international contributors and community members helping refine Hyprland's Lua ecosystem!

---

## License

This project is licensed under the [MIT License](LICENSE).
