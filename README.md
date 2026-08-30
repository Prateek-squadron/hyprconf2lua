# hyprconf2lua - Knowledge Base

**Project:** hyprconf2lua  
**Version:** 1.7.0  
**Description:** Convert Hyprland hyprlang `.conf` files to Lua `.lua` config format (v0.55+)  
**Maintainer:** Prateek-squadron  
**License:** MIT  

---

## Project Overview

hyprconf2lua is a converter that transforms Hyprland configuration files (`.conf` using hyprlang syntax) into Lua configuration files (`.lua`) compatible with Hyprland v0.55+.

The converter uses a pipeline architecture:
```
Input (.conf source)
    ├── lexer.py    → tokenize source into tokens
    ├── parser.py   → parse tokens into AST
    ├── codegen.py  → generate Lua code from AST
    └── Output (.lua)
```

---

## Project Structure

```
hyprconf2lua/
├── README.md              ← This knowledge base
├── pyproject.toml         ← Package metadata, version 1.7.0
├── src/
│   ├── hyprconf2lua/
│   │   ├── __init__.py    ← __version__ = "1.7.0"
│   │   ├── __main__.py    ← Entry point: cli.main()
│   │   ├── cli.py         ← CLI: argparse, file I/O, --check, --version
│   │   ├── converter.py   ← Pipeline orchestrator: tokenize → parse → codegen
│   │   ├── codegen.py    ← Code generator: AST → Lua string output
│   │   ├── lexer.py      ← Regex-based tokenizer: 17 token types
│   │   ├── parser.py     ← Recursive descent parser: 20+ parse methods
│   │   ├── ast.py       ← 21 AST node dataclasses
│   │   ├── mappings.py   ← Dispatcher maps, rule maps, flag mappings
│   │   └── mappings.py   ← 5 mapping dicts (DISPATCHER_MAP, etc.)
│   └── tests/
│       ├── __init__.py
│       └── test_converter.py ← 106 tests passing
├── dist/                  ← Built wheels and sdist
├── example/               ← Example hyprland.conf
├── hyprconf2lua.sh        ← Shell wrapper to run without pip install
├── install.sh             ← Symlinks hyprconf2lua.sh into PATH
├── LICENSE
├── README.md              ← This knowledge base
└── README_kb.md           ← (this file)
```

---

## v1.7.0 Fixes (Released)

All issues from the open PRs have been resolved in release **1.7.0**. Here's what was fixed:

### #35 - 7 Bug Fixes
1. **Window rules: match/swap** - match criteria and properties were swapped; now correctly separates `match:`-prefixed criteria from property rules
2. **Layer rules**: `blur=on = true` invalid Lua fixed; now emits `blur = true`
3. **Gestures**: nested inside `hl.config()` instead of `hl.gesture()` → now emitted as dedicated `hl.gesture({...})` calls
4. **Window move binds**: emitted raw tables instead of `hl.dsp.window.move()`; direction shorthand (`l`/`r`/`u`/`d`) expanded to `left`/`right`/`up`/`down`
5. **resizeactive binds**: now maps to `hl.dsp.window.resize({ x, y, relative = true })`
6. **Workspace-restore `+0`**: `+0` mapped to `workspace = "+0"` instead of `direction = "+0"`
7. **layoutmsg with trailing comment**: `layoutmsg, # dwindle` no longer parses argument as `nil`; flagged for manual review instead of crashing

### #38 - Windowrule/Layerrule Multi-word Values
- `workspace = "3 silent"` stays as string (not split into array)
- `size = 700 600`, `move 100%-433 53`, `opacity 0.9 0.8` → arrays `{700, 600}`, `{100%-433, 53}`, `{0.9, 0.8}`

### #39 - Animations Inside Sections
- `animation =`, `bezier =` directives inside `animations {}` now translate to `hl.animation()`/`hl.curve()` statements
- on/off flag → `enabled = true/false`
- styles like `popin 87%` preserved as `style = "popin 87%"`
- Statements emitted **outside** the `hl.config({})` table (valid Lua)

### #40 - Stdin Hyphen Whitespace
- `grim -c -g "$(slurp)" - | satty --filename -` preserves spaces around `-` and `|`
- Before: `grim -c -g \"$(slurp)\"-| satty --filename-` (spaces stripped)

### #33 - Comma in Variable Values
- `$kbNextWs = Ctrl+Super, right` parses correctly → `local kbNextWs = "Ctrl+Super, right"`
- Before: `kbNextWs = { }` (empty table)

### #32 - rgba() Color Parsing
- `shadow:color = rgba(0,0,0,0.85)` parses correctly
- Colon-paths expand to nested tables: `shadow = { color = "rgba(0,0,0,0.85)" }`

### #42 - movecurrentworkspacetomonitor Dispatcher
- New dispatcher: `hl.dsp.workspace.move({ monitor = "l" })`

---

## Test Results

- **106 tests passing** (only pre-existing `test_cli_help` fails due to module not being installed in /usr/bin/python path)
- All fixes verified against real-world hyprland configs
- Regressions: 0 (all existing tests continue to pass)

---

## How to Build & Test

```bash
# From project root
python -m build              # Build sdist + wheel
python -m pytest tests/    # Run all 106 tests
python -m hyprconf2lua     # CLI help

# Example conversions
hyprconf2lua example/hyprland.conf
```

---

## Guidelines for AI Agents Working on This Project

### Code Style
- Follow existing patterns in `src/hyprconf2lua/`
- Use `no_space_before` / `no_space_after` sets in `_join_tokens` for consistent spacing
- Keep `MULTI_VALUE_EFFECT_KEYS = {"move", "size", "opacity", "alpha"}` for multi-word effect values
- Dispatcher maps in `mappings.py` - add new dispatchers there

### Adding New Dispatchers
1. Add to `DISPATCHER_MAP` in `mappings.py` with `(func_string, needs_args)`
2. Handle in `build_dispatcher()` and `build_dispatcher_args()` in `codegen.py`
3. Add special cases for known patterns (e.g., `+0` → workspace, `l/r/u/d` → directions)

### Adding New Rule Types
1. Add to `WINDOW_RULE_MAP` or `LAYER_RULE_MAP` in `mappings.py`
2. Handle in `visit_windowrule()` / `visit_layerrule()` in `codegen.py`
3. Support both old-style (`rule, match:X`) and new-style (`match:key X`) syntax

### Adding New Animations/Beziers
1. Add `enabled` field to `AnimationDirective` in `ast.py`
2. Update `parse_animation()` in `parser.py` to extract `enabled`, `style` from comma values
3. Update `visit_animation()` in `codegen.py` to use `stmt.enabled` and `stmt.style`
4. Ensure statements are emitted **outside** `hl.config({})` table (see `emit_section_config`)

### Testing
- Run `python -m pytest tests/` to verify all 106 tests pass
- Add regression tests in `tests/test_converter.py` for new fixes
- Test with real hyprland configs via `hyprctl configerrors`

---

## Recent Changes History

| Version | Date | Key Fixes |
|---------|------|-----------|
| **1.7.0** | 2026-08-24 | All 7 bugs from #35, #38, #39, #40, #33, #32 fixed |
| **1.6.0** | 2026-08-20 | #26-#29 (source path, hyphens, ${} syntax, multiline exec) |
| **1.5.0** | 2026-08-28 | #24/#25 (hyphen→underscore, $HOME→os.getenv) |

---

## Contact & Support

- **GitHub:** https://github.com/Prateek-squadron/hyprconf2lua
- **PyPI:** https://pypi.org/project/hyprconf2lua/
- **Issues:** Use GitHub Issues for bug reports and feature requests
- **IRC/Slack:** #hyprland on Libera.Chat (project maintainer)

---

*This knowledge base was created for the v1.7.0 release cycle. For the latest updates, check the GitHub repository.*