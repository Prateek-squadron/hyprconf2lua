from __future__ import annotations
from typing import Dict, Optional, Tuple

from hyprconf2lua.lexer import tokenize, LexerError
from hyprconf2lua.parser import parse_config, ParserError
from hyprconf2lua.codegen import Codegen


class ConversionError(Exception):
    pass


class ConversionResult:
    def __init__(self, lua: str, report: dict, errors: list, warnings: list):
        self.lua = lua
        self.report = report
        self.errors = errors
        self.warnings = warnings

    @property
    def success(self) -> bool:
        return len(self.errors) == 0

    @property
    def coverage(self) -> float:
        total = self.report.get("translated", 0) + self.report.get("passthrough", 0) + self.report.get("flagged", 0)
        if total == 0:
            return 100.0
        return round(self.report.get("translated", 0) / total * 100, 1)


def convert(source: str) -> ConversionResult:
    errors: list = []
    warnings: list = []

    try:
        tokens = tokenize(source)
    except LexerError as e:
        errors.append(str(e))
        return ConversionResult("", {"translated": 0, "passthrough": 0, "flagged": 0}, errors, warnings)

    try:
        config = parse_config(source)
    except ParserError as e:
        errors.append(str(e))
        return ConversionResult("", {"translated": 0, "passthrough": 0, "flagged": 0}, errors, warnings)

    gen = Codegen()
    try:
        lua = gen.generate(config)
    except Exception as e:
        errors.append(f"Code generation error: {e}")
        return ConversionResult("", {"translated": 0, "passthrough": 0, "flagged": 0}, errors, warnings)

    report = gen.get_report()

    if report["flagged"] > 0:
        warnings.append(f"{report['flagged']} directive(s) flagged for manual review")

    return ConversionResult(lua, report, errors, warnings)
