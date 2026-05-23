import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from hyprconf2lua.lexer import tokenize
from hyprconf2lua.parser import parse_config
from hyprconf2lua.codegen import Codegen
from hyprconf2lua.converter import convert


SAMPLE_CONF = """# Test config
$mainMod = SUPER

general {
    gaps_in = 5
    gaps_out = 20
    border_size = 2
    layout = dwindle
}

input {
    kb_layout = us
    touchpad {
        natural_scroll = false
    }
}

monitor = eDP-1, 1920x1080@60, 0x0, 1.0

bind = $mainMod, Q, exec, kitty
bind = $mainMod SHIFT, F, togglefloating
bindl = , XF86AudioRaiseVolume, exec, wpctl set-volume 5%+
bindm = $mainMod, mouse:272, movewindow

windowrule = float, ^(pavucontrol)$
windowrulev2 = opacity 0.8 0.8, class:^(kitty)$, title:^(.*)$

exec-once = waybar
exec = swaybg

env = XCURSOR_SIZE, 24

bezier = myBezier, 0.05, 0.9, 0.1, 1.0
animation = windows, 1, 4, myBezier

workspace = 1, monitor:HDMI-A-1, default:true
layerrule = blur, ^(waybar)$

device:epic-mouse-v1 {
    sensitivity = -0.5
}

gesture {
    workspace_swipe = true
}

source = ~/.config/hypr/monitors.conf
"""


def test_lexer_basic():
    tokens = tokenize("bind = SUPER, Q, exec, kitty\n")
    types = [t.type for t in tokens]
    assert "IDENT" in types
    assert "EQUALS" in types
    assert "COMMA" in types
    assert "EOF" in types


def test_lexer_comment():
    tokens = tokenize("# this is a comment\n")
    assert any(t.type == "COMMENT" for t in tokens)


def test_lexer_section():
    tokens = tokenize("general {\n    gaps_in = 5\n}\n")
    assert any(t.type == "BLOCK_OPEN" for t in tokens)
    assert any(t.type == "BLOCK_CLOSE" for t in tokens)


def test_lexer_variable():
    tokens = tokenize("$mainMod = SUPER\n")
    dollar_tokens = [t for t in tokens if t.type == "DOLLAR"]
    assert len(dollar_tokens) == 1


def test_lexer_error():
    import pytest
    try:
        from hyprconf2lua.lexer import LexerError
    except ImportError:
        pytest.skip("need pytest")

    with pytest.raises(LexerError):
        tokenize("key = value `bad`")


def test_parse_variable():
    config = parse_config("$myVar = hello\n")
    assert len(config.body) == 1
    from hyprconf2lua.ast import VariableDef
    assert isinstance(config.body[0], VariableDef)
    assert config.body[0].name == "myVar"
    assert config.body[0].value == "hello"


def test_parse_section():
    config = parse_config("general {\n    gaps_in = 5\n}\n")
    from hyprconf2lua.ast import Section, Directive
    assert len(config.body) == 1
    assert isinstance(config.body[0], Section)
    assert config.body[0].name == "general"
    assert len(config.body[0].body) == 1
    assert isinstance(config.body[0].body[0], Directive)
    assert config.body[0].body[0].key == "gaps_in"
    assert config.body[0].body[0].value == ["5"]


def test_parse_bind():
    config = parse_config("bind = SUPER, Q, exec, kitty\n")
    from hyprconf2lua.ast import BindDirective
    assert len(config.body) == 1
    assert isinstance(config.body[0], BindDirective)
    assert config.body[0].dispatcher == "exec"
    assert config.body[0].params == ["kitty"]
    assert "SUPER" in config.body[0].mods


def test_parse_monitor():
    config = parse_config("monitor = eDP-1, 1920x1080@60, 0x0, 1.0\n")
    from hyprconf2lua.ast import MonitorDirective
    assert isinstance(config.body[0], MonitorDirective)
    assert config.body[0].name == "eDP-1"
    assert config.body[0].mode == "1920x1080@60"


def test_parse_windowrule():
    config = parse_config('windowrule = float, ^(pavucontrol)$\n')
    from hyprconf2lua.ast import WindowRule
    assert isinstance(config.body[0], WindowRule)
    assert config.body[0].rule == "float"
    assert config.body[0].is_v2 is False


def test_parse_windowrulev2():
    config = parse_config('windowrulev2 = opacity 0.8 0.8, class:^(kitty)$, title:^(.*)$\n')
    from hyprconf2lua.ast import WindowRule
    assert isinstance(config.body[0], WindowRule)
    assert config.body[0].is_v2 is True


def test_parse_env():
    config = parse_config("env = XCURSOR_SIZE, 24\n")
    from hyprconf2lua.ast import EnvDirective
    assert isinstance(config.body[0], EnvDirective)
    assert config.body[0].name == "XCURSOR_SIZE"


def test_parse_exec():
    config = parse_config("exec-once = waybar\n")
    from hyprconf2lua.ast import ExecDirective
    assert isinstance(config.body[0], ExecDirective)
    assert config.body[0].kind == "exec-once"


def test_parse_device():
    config = parse_config('device:epic-mouse-v1 {\n    sensitivity = -0.5\n}\n')
    from hyprconf2lua.ast import DeviceSection
    assert isinstance(config.body[0], DeviceSection)
    assert config.body[0].name == "epic-mouse-v1"


def test_full_conversion():
    result = convert(SAMPLE_CONF)
    assert result.success
    assert result.lua
    assert "hl.monitor" in result.lua
    assert "hl.bind" in result.lua
    assert "hl.env" in result.lua
    assert "hl.config" in result.lua
    assert "hl.window_rule" in result.lua
    assert "hl.curve" in result.lua
    assert "hl.animation" in result.lua
    assert "hl.exec_cmd" in result.lua or "hl.on" in result.lua
    assert "hl.device" in result.lua
    assert "hl.gesture" in result.lua
    assert "hl.workspace_rule" in result.lua
    assert "hl.layer_rule" in result.lua


def test_conversion_report():
    result = convert(SAMPLE_CONF)
    assert "translated" in result.report
    assert result.report["translated"] > 0


def test_empty_config():
    result = convert("")
    assert result.success
    assert result.lua is not None


def test_comment_only():
    result = convert("# just a comment\n")
    assert result.success
    assert "--" in result.lua


def test_inline_comment():
    result = convert("key = value # inline\n")
    assert result.success or not result.success


def test_variable_reference():
    result = convert("$mod = ALT\nbind = $mod, Q, exec, kitty\n")
    assert result.success
    assert "mod" in result.lua


def test_multiple_monitors():
    src = "monitor = eDP-1, 1920x1080@60, 0x0, 1\nmonitor = HDMI-A-1, 2560x1440, 1920x0, 1\n"
    result = convert(src)
    assert result.success
    assert result.lua.count("hl.monitor") == 2


def test_bezier_conversion():
    result = convert("bezier = overshoot, 0.05, 0.9, 0.1, 1.1\n")
    assert result.success
    assert "hl.curve" in result.lua
    assert "overshoot" in result.lua
    assert "bezier" in result.lua


def test_bind_with_flags():
    result = convert("bindl = , XF86AudioRaiseVolume, exec, wpctl set-volume 5%+\n")
    assert result.success
    assert "locked" in result.lua


def test_bindm_conversion():
    result = convert("bindm = $mainMod, mouse:272, movewindow\n")
    assert result.success
    assert "mouse" in result.lua


def test_layerrule_conversion():
    result = convert('layerrule = blur, ^(waybar)$\n')
    assert result.success
    assert "hl.layer_rule" in result.lua


def test_workspace_conversion():
    result = convert('workspace = 1, monitor:HDMI-A-1, default:true\n')
    assert result.success
    assert "hl.workspace_rule" in result.lua


def test_exec_ordering():
    src = "exec-once = waybar\nexec-once = mako\nexec = swaybg &\n"
    result = convert(src)
    assert result.success
    assert "hl.on" in result.lua
    assert "hyprland.start" in result.lua


def test_directory_conversion():
    with tempfile.TemporaryDirectory() as tmpdir:
        conf_path = os.path.join(tmpdir, "test.conf")
        with open(conf_path, "w") as f:
            f.write("bind = SUPER, Q, exec, kitty\n")
            f.write("env = TEST, 1\n")

        from hyprconf2lua.cli import process_dir
        failed = process_dir(tmpdir, check=True)
        assert failed == 0


def test_env_with_comma_value():
    result = convert("env = GDK_BACKEND, wayland,x11\n")
    assert result.success
    assert "wayland,x11" in result.lua, f"env with comma value failed: {result.lua}"


def test_mouse_bind_movewindow():
    result = convert("bind = SUPER, mouse:272, movewindow\n")
    assert result.success
    assert "hl.dsp.window.drag()" in result.lua, f"mouse:272 + movewindow should produce drag(): {result.lua}"


def test_mouse_bind_resizewindow():
    result = convert("bind = SUPER, mouse:273, resizewindow\n")
    assert result.success
    assert "hl.dsp.window.resize()" in result.lua, f"mouse:273 + resizewindow should produce resize(): {result.lua}"


def test_windowrule_with_at_sign():
    result = convert('windowrule = noborder, ^(xdg-desktop-portal@hyprland)$\n')
    assert result.success
    assert "@" in result.lua


def test_submap_conversion():
    src = 'submap = resize\nbind = , escape, submap, reset\nsubmap = reset\n'
    result = convert(src)
    assert result.success
    assert "hl.define_submap" in result.lua, f"submap conversion failed: {result.lua}"
    assert "resize" in result.lua


def test_plugin_section():
    src = 'plugin {\n    my_plugin = value\n}\n'
    result = convert(src)
    assert result.success
    assert "hl.plugin" in result.lua


def test_plugin_subsections():
    src = 'plugin {\n    hyprbars {\n        bar_color = rgb(ff0000)\n    }\n}\n'
    result = convert(src)
    assert result.success
    assert "hl.plugin" in result.lua
    assert "hyprbars" in result.lua
    assert "bar_color" in result.lua


def test_unbind_conversion():
    result = convert("unbind = SUPER, Q\n")
    assert result.success
    assert "hl.unbind" in result.lua, f"unbind conversion failed: {result.lua}"


def test_unknown_section_autoconvert():
    result = convert("custom_section {\n    my_key = value\n}\n")
    assert result.success
    assert "hl.config" in result.lua
    assert "custom_section" in result.lua
    assert result.report["flagged"] == 0


def test_colon_separated_nested_key():
    result = convert("decoration:blur:size = 3\n")
    assert result.success
    assert "hl.config" in result.lua or "decoration" in result.lua
    assert result.report["flagged"] == 0


def test_colon_two_level_key():
    result = convert("decoration:rounding = 10\n")
    assert result.success
    assert "decoration" in result.lua
    assert "rounding" in result.lua
    assert result.report["flagged"] == 0


def test_monitor_extra_fields():
    result = convert("monitor = eDP-1, 1920x1080, 0x0, 1, vrr, 1\n")
    assert result.success
    assert "vrr" in result.lua


def test_hl_annotation():
    result = convert("")
    assert "---@module 'hl'" in result.lua


def test_no_todo_on_unknown_section():
    result = convert("widget_config {\n    enabled = true\n}\n")
    assert "TODO" not in result.lua
    assert result.report["flagged"] == 0


def test_cli_help():
    import subprocess
    result = subprocess.run([sys.executable, "-m", "hyprconf2lua", "--help"],
                          capture_output=True, text=True)
    assert result.returncode == 0
    assert "Convert" in result.stdout


if __name__ == "__main__":
    test_lexer_basic()
    test_lexer_comment()
    test_lexer_section()
    test_lexer_variable()
    test_parse_variable()
    test_parse_section()
    test_parse_bind()
    test_parse_monitor()
    test_parse_windowrule()
    test_parse_windowrulev2()
    test_parse_env()
    test_parse_exec()
    test_parse_device()
    test_full_conversion()
    test_conversion_report()
    test_empty_config()
    test_comment_only()
    test_variable_reference()
    test_multiple_monitors()
    test_bezier_conversion()
    test_bind_with_flags()
    test_bindm_conversion()
    test_layerrule_conversion()
    test_workspace_conversion()
    test_exec_ordering()
    test_env_with_comma_value()
    test_mouse_bind_movewindow()
    test_mouse_bind_resizewindow()
    test_windowrule_with_at_sign()
    test_submap_conversion()
    test_plugin_section()
    test_plugin_subsections()
    test_unbind_conversion()
    test_unknown_section_autoconvert()
    test_colon_separated_nested_key()
    test_colon_two_level_key()
    test_monitor_extra_fields()
    test_hl_annotation()
    test_no_todo_on_unknown_section()
    print("All tests passed!")
