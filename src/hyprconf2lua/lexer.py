from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import List


TOKEN_SPECS = [
    ("COMMENT",    r"#[^\n]*"),
    ("BLOCK_OPEN", r"\{"),
    ("BLOCK_CLOSE", r"\}"),
    ("EQUALS",     r"="),
    ("COMMA",      r","),
    ("DOT",        r"\."),
    ("COLON",      r":"),
    ("DOLLAR",     r"\$"),
    ("STRING",     r'"([^"\\]|\\.)*"'),
    ("IDENT",      r'[^\s#={},:]+'),
    ("NEWLINE",    r"\n"),
    ("SKIP",       r"[ \t]+"),
    ("MISMATCH",   r"."),
]


@dataclass
class Token:
    type: str
    value: str
    line: int
    col: int

    def __repr__(self) -> str:
        return f"Token({self.type}, {self.value!r}, L{self.line}:{self.col})"


TOKEN_REGEX = re.compile("|".join(f"(?P<{name}>{pattern})" for name, pattern in TOKEN_SPECS))


class LexerError(Exception):
    def __init__(self, message: str, line: int, col: int):
        self.line = line
        self.col = col
        super().__init__(f"L{line}:{col}: {message}")


def tokenize(source: str) -> List[Token]:
    tokens: List[Token] = []
    line = 1
    last_line_start = 0

    def _col(pos: int) -> int:
        return pos - last_line_start + 1

    for m in TOKEN_REGEX.finditer(source):
        kind = m.lastgroup
        value = m.group()
        pos = m.start()

        if kind == "NEWLINE":
            line += 1
            last_line_start = pos + 1
            tokens.append(Token("NEWLINE", value, line - 1, _col(pos)))
        elif kind == "SKIP":
            pass
        elif kind == "COMMENT":
            tokens.append(Token("COMMENT", value, line, _col(pos)))
        elif kind == "MISMATCH":
            raise LexerError(f"Unexpected character: {value!r}", line, _col(pos))
        elif kind == "STRING":
            tokens.append(Token("STRING", value[1:-1], line, _col(pos)))
        else:
            tokens.append(Token(kind, value, line, _col(pos)))

    tokens.append(Token("EOF", "", line, 1))
    return tokens
