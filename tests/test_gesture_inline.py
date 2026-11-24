"""One-line `gesture =` conversion (Prateek-squadron/hyprconf2lua#62).

The expected field layout follows Hyprland v0.54.3's CConfigManager::handleGesture,
as exercised by the harness in the verification/issue-62-hyprland-0.54.3-gestures/
directory of https://github.com/sinback/hyprconf2lua/tree/example/fix-mods-for-gestures-testing
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from hyprconf2lua.converter import convert

FIELD_RE = re.compile(r'^\s*(--\s*)?\["(\w+)"\] = (.+),$')


def gestures(lua: str):
    """Return the field tables of every hl.gesture({...}) call, live or commented out."""
    tables, current = [], None
    for line in lua.splitlines():
        if line.lstrip("- ").startswith("hl.gesture({"):
            current = {}
        elif current is not None and line.lstrip("- ").startswith("})"):
            tables.append(current)
            current = None
        elif current is not None:
            m = FIELD_RE.match(line)
            assert m, f"unexpected line inside hl.gesture: {line!r}"
            current[m.group(2)] = m.group(3)
    return tables


def one_gesture(src: str):
    result = convert(src)
    assert result.success, result.errors
    tables = gestures(result.lua)
    assert len(tables) == 1, result.lua
    return result, tables[0]


def test_issue_62_mod_is_not_the_action():
    _, g = one_gesture("gesture = 3, up, mod: SUPER, fullscreen\n")
    assert g == {"fingers": "3", "direction": '"up"', "mods": '"SUPER"', "action": '"fullscreen"'}


def test_scale_option():
    _, g = one_gesture("gesture = 3, up, scale: 1.5, close\n")
    assert g == {"fingers": "3", "direction": '"up"', "scale": "1.5", "action": '"close"'}


def test_options_in_either_order():
    _, a = one_gesture("gesture = 3, up, mod: SUPER, scale: 1.5, close\n")
    _, b = one_gesture("gesture = 3, up, scale: 1.5, mod: SUPER, close\n")
    assert a["mods"] == b["mods"] == '"SUPER"'
    assert a["scale"] == b["scale"] == "1.5"
    assert a["action"] == b["action"] == '"close"'


def test_repeated_option_last_wins():
    _, g = one_gesture("gesture = 3, up, mod: SUPER, mod: ALT, close\n")
    assert g["mods"] == '"ALT"'


def test_multi_modifier_mods():
    _, g = one_gesture("gesture = 3, up, mod: SUPER SHIFT, close\n")
    assert g["mods"] == '"SUPER SHIFT"'


def test_mod_from_variable():
    _, g = one_gesture("$mainMod = SUPER\ngesture = 3, up, mod: $mainMod, close\n")
    assert g["mods"] == '"SUPER"'


def test_mod_after_action_becomes_action_arg():
    # Hyprland hands the field after `fullscreen` to it as its mode, not as a modifier.
    _, g = one_gesture("gesture = 3, up, fullscreen, mod: SUPER\n")
    assert "mods" not in g
    assert g["mode"] == '"mod:SUPER"'


def test_mod_after_argless_action_is_ignored_with_note():
    result, g = one_gesture("gesture = 3, up, close, mod: SUPER\n")
    assert "mods" not in g
    assert "-- NOTE: Hyprland ignores trailing gesture field(s): mod:SUPER" in result.lua
    assert result.report["flagged"] == 0


def test_no_options_unchanged():
    _, g = one_gesture("gesture = 3, horizontal, workspace\n")
    assert g == {"fingers": "3", "direction": '"horizontal"', "action": '"workspace"'}


def test_trailing_empty_field_is_harmless():
    result, g = one_gesture("gesture = 4, swipe, move,\n")
    assert g == {"fingers": "4", "direction": '"swipe"', "action": '"move"'}
    assert "NOTE" not in result.lua


def test_action_args_map_to_named_fields():
    _, g = one_gesture("gesture = 3, up, fullscreen, maximized\n")
    assert g["mode"] == '"maximized"'
    _, g = one_gesture("gesture = 3, down, float, tile\n")
    assert g["mode"] == '"tile"'
    _, g = one_gesture("gesture = 4, left, special, magic\n")
    assert g["workspace_name"] == '"magic"'
    _, g = one_gesture("gesture = 3, pinch, cursorZoom, 1.5, live\n")
    assert g["zoom_level"] == '"1.5"'
    assert g["mode"] == '"live"'


def test_string_fields_are_not_coerced_to_booleans():
    # hl.gesture reads `mode` with a string parser, which rejects Lua booleans.
    _, g = one_gesture("gesture = 3, down, float, on\n")
    assert g["mode"] == '"on"'


def test_gesturep_sets_disable_inhibit():
    _, g = one_gesture("gesturep = 3, up, close\n")
    assert g["disable_inhibit"] == "true"


def test_plain_gesture_has_no_disable_inhibit():
    _, g = one_gesture("gesture = 3, up, close\n")
    assert "disable_inhibit" not in g


def test_scale_clamped_like_hyprlang():
    result, g = one_gesture("gesture = 3, up, scale: 20, close\n")
    assert g["scale"] == "10"
    assert "clamped to 10" in result.lua
    _, g = one_gesture("gesture = 3, up, scale: 0.01, close\n")
    assert g["scale"] == "0.1"


def test_dispatcher_gesture_is_flagged_and_commented_out():
    result = convert("gesture = 3, left, mod: SUPER, dispatcher, workspace, e+1\n")
    assert result.success
    assert result.report["flagged"] == 1
    assert result.report["translated"] == 0
    assert "-- TODO: manual review (gesture dispatcher: workspace, e+1)" in result.lua
    # no live hl.gesture call is emitted for it
    assert not any(line.startswith("hl.gesture") for line in result.lua.splitlines())
    (g,) = gestures(result.lua)
    assert g["mods"] == '"SUPER"'


def test_gesture_inside_gestures_section():
    result = convert("gestures {\n    gesture = 3, horizontal, mod: ALT, workspace\n}\n")
    assert result.success
    (g,) = gestures(result.lua)
    assert g["mods"] == '"ALT"'
    assert g["action"] == '"workspace"'


def test_options_before_direction_are_not_reinterpreted():
    # Hyprland rejects this line (direction slot holds `mod:`); the converter must not
    # quietly turn it into a valid modded gesture.
    _, g = one_gesture("gesture = 3, mod: SUPER, up, fullscreen\n")
    assert "mods" not in g
    assert g["direction"] == '"mod:SUPER"'


def test_counted_once_in_report():
    result = convert("gesture = 3, up, mod: SUPER, fullscreen\n")
    assert result.report == {"translated": 1, "passthrough": 0, "flagged": 0}
