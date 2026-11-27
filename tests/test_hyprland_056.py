import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from hyprconf2lua.converter import convert
from hyprconf2lua.parser import ParserError


class TestBinddAndFlags:
    def test_bindd_simple(self):
        result = convert("bindd = SUPER, Q, Close active window, killactive\n")
        assert result.success
        assert 'hl.bind("SUPER + Q", hl.dsp.window.close(), { description = "Close active window" })' in result.lua

    def test_bindd_with_flags(self):
        result = convert("bindde = , XF86AudioRaiseVolume, Volume up, exec, wpctl set-volume 5%+\n")
        assert result.success
        assert 'hl.bind("XF86AudioRaiseVolume", hl.dsp.exec_cmd("wpctl set-volume 5%+"), { repeating = true, description = "Volume up" })' in result.lua

    def test_bindd_insufficient_args_raises(self):
        result = convert("bindd = SUPER, Q, killactive\n")
        assert not result.success
        assert any("bindd needs at least 4 arguments" in e for e in result.errors)

    def test_bindx_allow_input_capture(self):
        result = convert("bindx = SUPER, X, exec, foo\n")
        assert result.success
        assert 'hl.bind("SUPER + X", hl.dsp.exec_cmd("foo"), { allow_input_capture = true })' in result.lua

    def test_bindxl_combined(self):
        result = convert("bindxl = SUPER, Y, exec, bar\n")
        assert result.success
        assert "locked = true" in result.lua
        assert "allow_input_capture = true" in result.lua

    def test_bindu_submap_universal(self):
        result = convert("bindu = SUPER, Escape, submap, reset\n")
        assert result.success
        assert "submap_universal = true" in result.lua

    def test_bindo_long_press(self):
        result = convert("bindo = SUPER, Space, exec, rofi\n")
        assert result.success
        assert "long_press = true" in result.lua

    def test_bindc_and_bindg(self):
        result_c = convert("bindc = SUPER, mouse:272, exec, click_app\n")
        assert result_c.success
        assert "click = true" in result_c.lua
        assert "release = true" in result_c.lua

        result_g = convert("bindg = SUPER, mouse:272, exec, drag_app\n")
        assert result_g.success
        assert "drag = true" in result_g.lua
        assert "release = true" in result_g.lua


class TestDispatcherSimplification:
    def test_exec_hyprctl_dispatch_togglefloating(self):
        result = convert("bind = SUPER, F, exec, hyprctl dispatch togglefloating\n")
        assert result.success
        assert 'hl.bind("SUPER + F", hl.dsp.window.float())' in result.lua

    def test_exec_hyprctl_dispatch_with_arg(self):
        result = convert("bind = SUPER, 1, exec, hyprctl dispatch workspace 1\n")
        assert result.success
        assert 'hl.bind("SUPER + 1", hl.dsp.focus({ workspace = 1 }))' in result.lua

    def test_exec_hyprctl_dispatch_with_comma_arg(self):
        result = convert("bind = SUPER, 2, exec, hyprctl dispatch workspace, 2\n")
        assert result.success
        assert 'hl.bind("SUPER + 2", hl.dsp.focus({ workspace = 2 }))' in result.lua

    def test_exec_hyprctl_non_dispatch_kept(self):
        result = convert("bind = SUPER, R, exec, hyprctl reload\n")
        assert result.success
        assert 'hl.bind("SUPER + R", hl.dsp.exec_cmd("hyprctl reload"))' in result.lua

    def test_releaseinputcapture_dispatcher(self):
        result = convert("bind = SUPER, Z, releaseinputcapture\n")
        assert result.success
        assert 'hl.bind("SUPER + Z", hl.dsp.release_input_capture())' in result.lua

    def test_mouse_resizewindow_aspect_ratio(self):
        result = convert(
            "bindm = ALT, mouse:273, resizewindow 1\n"
            "bindm = ALT, mouse:274, resizewindow 2\n"
            "bindm = ALT, mouse:275, resizewindow 0\n"
            "bindm = ALT, mouse:276, resizewindow\n"
        )
        assert result.success
        assert 'hl.bind("ALT + mouse:273", hl.dsp.window.resize({ keep_aspect_ratio = true }), { mouse = true })' in result.lua
        assert 'hl.bind("ALT + mouse:274", hl.dsp.window.resize({ keep_aspect_ratio = false }), { mouse = true })' in result.lua
        assert 'hl.bind("ALT + mouse:275", hl.dsp.window.resize(), { mouse = true })' in result.lua
        assert 'hl.bind("ALT + mouse:276", hl.dsp.window.resize(), { mouse = true })' in result.lua


class TestPermissionDirective:
    def test_permission_valid(self):
        result = convert(
            "permission = ^(/usr/lib/xdg-desktop-portal-hyprland)$, screencopy, allow\n"
            "permission = /usr/bin/grim, screencopy, allow\n"
            "permission = .*, audio_capture, ask\n"
        )
        assert result.success
        assert 'hl.permission({ binary = "^(/usr/lib/xdg-desktop-portal-hyprland)$", type = "screencopy", mode = "allow" })' in result.lua
        assert 'hl.permission({ binary = "/usr/bin/grim", type = "screencopy", mode = "allow" })' in result.lua
        assert 'hl.permission({ binary = ".*", type = "audio_capture", mode = "ask" })' in result.lua

    def test_permission_malformed_flagged(self):
        result = convert("permission = incomplete\n")
        assert "TODO: manual review (malformed permission: expected binary, type, mode)" in result.lua
        assert result.report["flagged"] == 1


class TestMonitorV2:
    def test_monitorv2_block(self):
        src = """
monitorv2 {
    output = DP-1
    mode = 2560x1440@165
    position = 0x0
    scale = 1
    disabled = 0
    vrr = 1
}
"""
        result = convert(src)
        assert result.success
        assert "hl.monitor({" in result.lua
        assert 'output = "DP-1"' in result.lua
        assert 'mode = "2560x1440@165"' in result.lua
        assert 'position = "0x0"' in result.lua
        assert "scale = 1" in result.lua
        assert "disabled = false" in result.lua
        assert "vrr = 1" in result.lua

    def test_monitorv2_colon_named_block(self):
        src = """
monitorv2:HDMI-A-1 {
    mode = 1920x1080@60
    position = auto
    scale = 1
    disabled = 1
}
"""
        result = convert(src)
        assert result.success
        assert "hl.monitor({" in result.lua
        assert 'output = "HDMI-A-1"' in result.lua
        assert 'mode = "1920x1080@60"' in result.lua
        assert 'position = "auto"' in result.lua
        assert "disabled = true" in result.lua

    def test_monitorv2_reserved_gap(self):
        src = """
monitorv2 {
    output = eDP-1
    reserved = 10 20 30 40
}
"""
        result = convert(src)
        assert result.success
        assert "reserved = { top = 10, right = 20, bottom = 30, left = 40 }" in result.lua

    def test_input_capture_section(self):
        src = """
input-capture {
    capture_modifiers = true
    enforce_barriers = false
}
"""
        result = convert(src)
        assert result.success
        assert "input_capture = {" in result.lua
        assert "capture_modifiers = true" in result.lua
        assert "enforce_barriers = false" in result.lua
