import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))

from scripts.build_web import build_bundle


def test_build_web_bundle():
    build_bundle()
    bundle_file = ROOT_DIR / "web" / "hyprconf2lua_bundle.js"
    assert bundle_file.exists()
    content = bundle_file.read_text(encoding="utf-8")
    assert "window.HYPRCONF2LUA_BUNDLE" in content
    assert "__init__.py" in content
    assert "converter.py" in content
    assert "parser.py" in content
    assert "codegen.py" in content
