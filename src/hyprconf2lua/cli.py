from __future__ import annotations
import argparse
import os
import sys

from hyprconf2lua.converter import convert


def convert_file(path: str, check: bool = False, report: bool = False) -> bool:
    try:
        with open(path, "r") as f:
            source = f.read()
    except FileNotFoundError:
        print(f"Error: file not found: {path}", file=sys.stderr)
        return False
    except IOError as e:
        print(f"Error: {e}", file=sys.stderr)
        return False

    result = convert(source)

    if result.errors:
        for err in result.errors:
            print(f"Error: {err}", file=sys.stderr)
        return False

    if result.warnings:
        for w in result.warnings:
            print(f"Warning: {w}", file=sys.stderr)

    if check:
        if result.report["flagged"] > 0:
            print(f"Check FAILED: {result.report['flagged']} flagged directives",
                  file=sys.stderr)
            return False
        return True

    return result.lua


def process_dir(dir_path: str, in_place: bool = False, check: bool = False,
                report: bool = False) -> int:
    failed = 0
    for root, dirs, files in os.walk(dir_path):
        for fname in files:
            if not fname.endswith(".conf"):
                continue
            fpath = os.path.join(root, fname)
            lua_path = os.path.splitext(fpath)[0] + ".lua"

            if not check and not in_place:
                continue

            lua_output = convert_file(fpath, check=check, report=report)
            if lua_output is False:
                failed += 1
                if check:
                    print(f"  FAIL: {fpath}", file=sys.stderr)
                continue

            if isinstance(lua_output, str):
                if check:
                    print(f"  PASS: {fpath}")
                    continue
                if in_place:
                    try:
                        with open(lua_path, "w") as f:
                            f.write(lua_output)
                        print(f"  WROTE: {lua_path}")
                    except IOError as e:
                        print(f"  ERROR writing {lua_path}: {e}", file=sys.stderr)
                        failed += 1

    return failed


def main():
    parser = argparse.ArgumentParser(
        description="Convert Hyprland hyprlang .conf to Lua .lua config (v0.55+)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  hyprconf2lua hyprland.conf > hyprland.lua
  hyprconf2lua --in hyprland.conf --out hyprland.lua
  hyprconf2lua --dir ~/.config/hypr --in-place
  cat hyprland.conf | hyprconf2lua > hyprland.lua
  hyprconf2lua --check hyprland.conf
        """,
    )
    parser.add_argument("file", nargs="?", help="Input .conf file (reads stdin if omitted)")
    parser.add_argument("-o", "--out", help="Output file (default: stdout)")
    parser.add_argument("-d", "--dir", help="Walk a directory, writing .lua next to each .conf")
    parser.add_argument("--in-place", action="store_true", help="With --dir, overwrite existing .lua siblings")
    parser.add_argument("--check", action="store_true", help="Exit 3 if any directive is flagged")
    parser.add_argument("--report", action="store_true", help="Print translation stats to stderr")
    parser.add_argument("--version", action="store_true", help="Print version and exit")

    args = parser.parse_args()

    if args.version:
        from hyprconf2lua import __version__
        print(f"hyprconf2lua v{__version__}")
        sys.exit(0)

    if args.dir:
        failed = process_dir(args.dir, in_place=args.in_place, check=args.check, report=args.report)
        if args.check and failed > 0:
            sys.exit(3)
        sys.exit(1 if failed > 0 else 0)

    source: str
    source_name: str = args.file or "stdin"

    if args.file:
        try:
            with open(args.file, "r") as f:
                source = f.read()
        except FileNotFoundError:
            print(f"Error: file not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        except IOError as e:
            print(f"Error reading {args.file}: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        if sys.stdin.isatty():
            parser.print_help()
            sys.exit(0)
        source = sys.stdin.read()

    result = convert(source)

    for err in result.errors:
        print(f"Error: {err}", file=sys.stderr)

    if result.errors:
        sys.exit(1)

    for w in result.warnings:
        print(f"Warning: {w}", file=sys.stderr)

    if not result.lua.strip():
        print("Error: conversion produced no output", file=sys.stderr)
        sys.exit(1)

    if args.report:
        r = result.report
        total = r["translated"] + r["passthrough"] + r["flagged"]
        cov = result.coverage
        print(f"Report: {r['translated']} translated, {r['passthrough']} passthrough, "
              f"{r['flagged']} flagged, {total} total, {cov}% coverage",
              file=sys.stderr)

    if args.check:
        if result.report["flagged"] > 0:
            print(f"Check FAILED: {result.report['flagged']} flagged directive(s)",
                  file=sys.stderr)
            sys.exit(3)
        sys.exit(0)

    if args.out:
        try:
            with open(args.out, "w") as f:
                f.write(result.lua)
        except IOError as e:
            print(f"Error writing {args.out}: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        sys.stdout.write(result.lua)
        sys.stdout.flush()


if __name__ == "__main__":
    main()
