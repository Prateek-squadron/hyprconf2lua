import sys
import os
sys.path.insert(0, os.path.abspath('src'))
from hyprconf2lua.converter import convert

def test_unresolved_var_in_bind():
    result = convert('bind = $kbSession, global, caelestia:session\n')
    print(result.lua)

if __name__ == "__main__":
    test_unresolved_var_in_bind()
