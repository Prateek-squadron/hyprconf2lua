"""Security hardening regression tests for hyprconf2lua."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from hyprconf2lua.cli import process_dir
from hyprconf2lua.converter import convert


def test_quote_escape_bypass_blocked():
    from hyprconf2lua.codegen import Codegen
    gen = Codegen()
    # Value starts and ends with '"' but has unescaped quotes inside.
    payload = '"x"); os.execute("id"); --"'
    quoted = gen.quote(payload)
    assert quoted == '"\\"x\\"); os.execute(\\"id\\"); --\\""'

    # End-to-end via exec-once (starts and ends with '"' with unescaped '"' inside)
    res = convert('exec-once = "x" .. os.execute("id") .. "y"\n')
    assert res.success
    assert 'os.execute("id")' not in res.lua
    assert '\\"id\\"' in res.lua


def test_mainmod_variable_escape():
    payload = '$mainMod = SUPER" .. os.execute("id") .. "\n'
    result = convert(payload)
    assert result.success
    assert 'os.execute("id")' not in result.lua
    assert 'local mainMod = "SUPER\\" .. os.execute(\\"id\\") .. \\""' in result.lua


def test_newline_escaped_in_quoted_string():
    from hyprconf2lua.codegen import Codegen
    gen = Codegen()
    escaped = gen.quote('hello\nworld\r!')
    assert escaped == '"hello\\nworld\\r!"'


def test_os_getenv_literal_injection_blocked():
    payload = 'exec-once = os.getenv(os.execute("id"))\n'
    result = convert(payload)
    assert result.success
    assert 'os.execute("id")' not in result.lua
    assert '\\"id\\"' in result.lua


def test_legitimate_env_var_still_expands():
    os.environ["HYPRCONF2LUA_TEST_VAR"] = "/tmp/test"
    try:
        result = convert("exec-once = $HYPRCONF2LUA_TEST_VAR/run.sh\n")
        assert result.success
        assert 'os.getenv("HYPRCONF2LUA_TEST_VAR")' in result.lua
    finally:
        del os.environ["HYPRCONF2LUA_TEST_VAR"]


def test_process_dir_refuses_symlink_overwrite():
    with tempfile.TemporaryDirectory() as tmpdir:
        target = os.path.join(tmpdir, "sensitive.txt")
        with open(target, "w") as f:
            f.write("DO_NOT_OVERWRITE\n")

        conf = os.path.join(tmpdir, "evil.conf")
        with open(conf, "w") as f:
            f.write("bind = SUPER, Q, exec, kitty\n")

        evil_lua = os.path.join(tmpdir, "evil.lua")
        os.symlink(target, evil_lua)

        failed = process_dir(tmpdir, in_place=True)
        assert failed == 1
        with open(target, "r") as f:
            assert f.read() == "DO_NOT_OVERWRITE\n"


def test_cli_out_refuses_symlink_overwrite():
    with tempfile.TemporaryDirectory() as tmpdir:
        target = os.path.join(tmpdir, "sensitive.txt")
        with open(target, "w") as f:
            f.write("DO_NOT_OVERWRITE\n")

        conf = os.path.join(tmpdir, "test.conf")
        with open(conf, "w") as f:
            f.write("bind = SUPER, Q, exec, kitty\n")

        out_link = os.path.join(tmpdir, "out.lua")
        os.symlink(target, out_link)

        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path(__file__).parent.parent / "src")
        proc = subprocess.run(
            [sys.executable, "-m", "hyprconf2lua", conf, "-o", out_link],
            capture_output=True,
            text=True,
            env=env,
        )
        assert proc.returncode == 1
        assert "symlink" in proc.stderr.lower()
        with open(target, "r") as f:
            assert f.read() == "DO_NOT_OVERWRITE\n"


def test_parser_max_nesting_depth_prevents_recursion_error():
    depth = 80
    conf = ("s {\n" * depth) + "x = 1\n" + ("}\n" * depth)
    result = convert(conf)
    assert not result.success
    assert any("Maximum nesting depth" in err for err in result.errors)
