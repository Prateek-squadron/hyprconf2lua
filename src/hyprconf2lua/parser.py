from __future__ import annotations
from typing import Dict, List, Optional

from hyprconf2lua.lexer import Token, LexerError
from hyprconf2lua.ast import *


BIND_PREFIXES = {"bindm", "binde", "bindr", "bindl", "bindn", "bindo",
                 "bindt", "bindi", "bindp", "bindc", "bindd"}

BIND_FLAG_MAP = {
    "bind":   "",
    "bindl":  "l",
    "bindr":  "r",
    "bindn":  "n",
    "bindo":  "",
    "bindm":  "m",
    "binde":  "",
    "bindt":  "t",
    "bindi":  "i",
    "bindp":  "p",
    "bindc":  "c",
    "bindd":  "d",
}


def _parse_combined_bind(directive: str) -> str:
    flags = ""
    if directive.startswith("bind"):
        remaining = directive[4:]
        for ch in remaining:
            flags += BIND_FLAG_MAP.get("bind" + ch, "")
    return flags


class ParserError(Exception):
    def __init__(self, message: str, token: Token):
        self.line = token.line
        self.col = token.col
        super().__init__(f"L{token.line}:{token.col}: {message}")


class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
        self.variables: Dict[str, str] = {}

    def peek(self) -> Token:
        return self.tokens[self.pos]

    def advance(self) -> Token:
        t = self.tokens[self.pos]
        self.pos += 1
        return t

    def expect(self, type_: str) -> Token:
        t = self.peek()
        if t.type != type_:
            raise ParserError(f"Expected {type_}, got {t.type} ({t.value!r})", t)
        return self.advance()

    def skip_newlines(self):
        while self.peek().type == "NEWLINE":
            self.advance()

    def parse(self) -> ConfigFile:
        body = self.parse_block(stop=None)
        return ConfigFile(body)

    def parse_block(self, stop: Optional[str] = None) -> Block:
        stmts: Block = []
        self.skip_newlines()
        while self.peek().type != "EOF" and (stop is None or self.peek().type != stop):
            stmt = self.parse_stmt()
            if stmt is not None:
                stmts.append(stmt)
            self.skip_newlines()
        return self._group_submaps(stmts)

    def _group_submaps(self, stmts: Block) -> Block:
        result: Block = []
        i = 0
        while i < len(stmts):
            s = stmts[i]
            if isinstance(s, Directive) and s.key == "submap" and s.value and s.value[0].strip().lower() != "reset":
                name = s.value[0].strip()
                body: Block = []
                i += 1
                while i < len(stmts):
                    inner = stmts[i]
                    if isinstance(inner, Directive) and inner.key == "submap":
                        val = inner.value[0].strip().lower() if inner.value else ""
                        if val == "reset":
                            i += 1
                            break
                    body.append(inner)
                    i += 1
                result.append(SubmapDef(name, body, s.line))
            elif isinstance(s, Directive) and s.key == "submap_reset":
                result.append(Comment("# submap = reset (orphan, no matching submap start)", s.line))
                i += 1
            else:
                result.append(s)
                i += 1
        return result

    def parse_stmt(self) -> Optional[BlockStmt]:
        t = self.peek()

        if t.type == "COMMENT":
            return self.parse_comment()
        if t.type == "BLOCK_CLOSE":
            return None
        if t.type == "DOLLAR":
            return self.parse_variable_def()
        if t.type == "IDENT":
            return self.parse_ident_stmt()
        if t.type == "NEWLINE":
            self.advance()
            return None
        if t.type == "EOF":
            return None

        raise ParserError(f"Unexpected token: {t.value!r}", t)

    def parse_comment(self) -> Comment:
        t = self.advance()
        return Comment(t.value, t.line)

    def parse_variable_def(self) -> VariableDef:
        self.advance()
        name_t = self.expect("IDENT")
        self.expect("EQUALS")
        val = self.parse_value_rest()
        return VariableDef(name_t.value, val, name_t.line)

    def parse_value_rest(self) -> str:
        parts = []
        while self.peek().type in ("IDENT", "STRING", "DOLLAR", "DOT", "COLON") or \
              (self.peek().type == "EQUALS" and parts):
            if self.peek().type == "COMMENT":
                break
            t = self.advance()
            if t.type == "DOLLAR":
                var_t = self.expect("IDENT")
                parts.append("$" + var_t.value)
            else:
                parts.append(t.value)
            if self.peek().type == "DOT":
                self.advance()
                parts.append(".")

        return self._join_tokens(parts)

    @staticmethod
    def _join_tokens(tokens: List[str]) -> str:
        if not tokens:
            return ""
        result = tokens[0]
        for t in tokens[1:]:
            no_space_before = {":", ",", "=", "+", "-", "%", "@", "^", "*", "|", "~"}
            no_space_after = {":", ",", "="}
            if t in no_space_before or result[-1:] in no_space_after:
                result += t
            else:
                result += " " + t
        return result.strip()

    def parse_comma_values(self) -> List[str]:
        values = []
        current = []
        while self.peek().type not in ("NEWLINE", "EOF") and \
              self.peek().type != "COMMENT":
            if self.peek().type == "BLOCK_CLOSE":
                break
            if self.peek().type == "BLOCK_OPEN":
                self.advance()
                current.append("{")
                depth = 1
                while depth > 0 and self.peek().type not in ("EOF", "NEWLINE"):
                    t = self.advance()
                    if t.type == "BLOCK_OPEN":
                        depth += 1
                    elif t.type == "BLOCK_CLOSE":
                        depth -= 1
                    if depth > 0:
                        current.append(t.value)
                if depth == 0:
                    current.append("}")
                continue
            if self.peek().type == "COMMA":
                self.advance()
                values.append(self._join_tokens(current))
                current = []
                continue
            if self.peek().type == "DOLLAR":
                self.advance()
                var_t = self.expect("IDENT")
                current.append("$" + var_t.value)
            else:
                t = self.advance()
                current.append(t.value)
        remaining = self._join_tokens(current)
        if remaining:
            values.append(remaining)
        return values

    def resolve_var(self, val: str) -> str:
        import re
        def _repl(m: re.Match) -> str:
            var_name = m.group(1)
            if var_name in self.variables:
                return self.variables[var_name]
            return m.group(0)
        return re.sub(r'\$(\w+)', _repl, val)

    def parse_ident_stmt(self) -> BlockStmt:
        t = self.advance()
        directive = t.value

        # Handle colon-separated nested keys: section:subsection:key
        colon_parts = [directive]
        while self.peek().type == "COLON":
            self.advance()
            if self.peek().type == "IDENT":
                colon_parts.append(self.advance().value)
            else:
                break
        directive = ":".join(colon_parts)

        if directive.startswith("bind"):
            if self.peek().type == "BLOCK_OPEN":
                return self.parse_general_directive(directive, t.line)
            return self.parse_bind(directive, t.line)

        if directive == "monitor":
            return self.parse_monitor(t.line)
        if directive == "windowrule":
            return self.parse_windowrule(False, t.line)
        if directive == "windowrulev2":
            return self.parse_windowrule(True, t.line)
        if directive == "exec-once" or directive == "execr-once":
            return self.parse_exec(directive, t.line)
        if directive == "exec":
            return self.parse_exec(directive, t.line)
        if directive == "exec-shutdown":
            return self.parse_exec(directive, t.line)
        if directive == "animation":
            return self.parse_animation(t.line)
        if directive == "bezier":
            return self.parse_bezier(t.line)
        if directive == "env":
            return self.parse_env(t.line)
        if directive == "source":
            return self.parse_source(t.line)
        if directive == "gesture":
            if self.peek().type == "BLOCK_OPEN":
                return self.parse_gesture(t.line)
            return self.parse_general_directive(directive, t.line)
        if directive == "workspace":
            return self.parse_workspace(t.line)
        if directive == "layerrule":
            return self.parse_layerrule(t.line)
        if directive == "submap":
            return self.parse_submap(t.line)

        colon_idx = directive.find(":")
        if colon_idx > 0:
            prefix = directive[:colon_idx]
            if prefix == "device":
                return self.parse_device(directive[colon_idx + 1:], t.line)

        # Handle colon-separated nested key: section:key = value
        if len(colon_parts) >= 3:
            section_name = colon_parts[0]
            sub_key = ":".join(colon_parts[1:])
            self.expect("EQUALS")
            val = self.parse_value_rest()
            body = [Directive(sub_key, [val], t.line, 0)]
            return Section(section_name, body, t.line)

        # Handle colon-separated section:key = value (two parts)
        if len(colon_parts) == 2:
            section_name = colon_parts[0]
            inner_key = colon_parts[1]
            self.expect("EQUALS")
            val = self.parse_value_rest()
            body = [Directive(inner_key, [val], t.line, 0)]
            return Section(section_name, body, t.line)

        return self.parse_general_directive(directive, t.line)

    def parse_general_directive(self, directive: str, line: int) -> Optional[BlockStmt]:
        t = self.peek()
        if t.type == "EQUALS":
            self.advance()
            values = self.parse_comma_values()
            return Directive(directive, values, line, 0)
        if t.type == "BLOCK_OPEN":
            self.advance()
            body = self.parse_block(stop="BLOCK_CLOSE")
            self.expect("BLOCK_CLOSE")
            return Section(directive, body, line)
        raise ParserError(f"Expected = or {{ after {directive!r}", t)

    def parse_bind(self, directive: str, line: int) -> BindDirective:
        flags = _parse_combined_bind(directive)
        self.expect("EQUALS")
        self.skip_newlines()
        values = self.parse_comma_values()
        if len(values) < 3:
            raise ParserError(f"bind needs at least 3 arguments (mods, key, dispatcher), got {len(values)}", Token("IDENT", directive, line, 0))
        mods_str = values[0].strip()
        key = values[1].strip()
        dispatcher = values[2].strip()
        if dispatcher in ("exec", "execr") and len(values) > 3:
            cmd = ",".join(v.strip() for v in values[3:]).strip()
            params = [cmd] if cmd else []
        else:
            params = [v.strip() for v in values[3:]]
        mods = [m.strip() for m in mods_str.replace(",", " ").split() if m.strip() and m.strip() != "&"] if mods_str else []
        return BindDirective(mods, key, dispatcher, params, flags, line)

    def parse_monitor(self, line: int) -> MonitorDirective:
        self.expect("EQUALS")
        values = self.parse_comma_values()
        name = values[0].strip() if len(values) > 0 else ""
        mode = values[1].strip() if len(values) > 1 else "preferred"
        position = values[2].strip() if len(values) > 2 else "auto"
        scale = values[3].strip() if len(values) > 3 else "1"
        extra = {}
        for i in range(4, len(values), 2):
            key = values[i].strip()
            val = values[i + 1].strip() if i + 1 < len(values) else "true"
            extra[key] = val
        return MonitorDirective(name, mode, position, scale, line, extra)

    def _parse_rule_block_body(self) -> tuple:
        """Parse windowrule/layerrule block content { ... }.
        Returns (name, match dict, effects dict)."""
        name = ""
        match: Dict[str, str] = {}
        effects: Dict[str, List[str]] = {}

        self.skip_newlines()
        self.expect("BLOCK_OPEN")
        self.skip_newlines()

        while self.peek().type not in ("BLOCK_CLOSE", "EOF"):
            t = self.peek()
            if t.type == "COMMENT":
                self.advance()
            elif t.type == "IDENT":
                key_parts = [self.advance().value]
                while self.peek().type == "COLON":
                    self.advance()
                    if self.peek().type == "IDENT":
                        key_parts.append(self.advance().value)
                    else:
                        break
                key = ":".join(key_parts)

                if key == "match" and self.peek().type == "BLOCK_OPEN":
                    self.advance()
                    self.skip_newlines()
                    while self.peek().type not in ("BLOCK_CLOSE", "EOF"):
                        t2 = self.peek()
                        if t2.type == "COMMENT":
                            self.advance()
                        elif t2.type == "IDENT":
                            mk_parts = [self.advance().value]
                            while self.peek().type == "COLON":
                                self.advance()
                                if self.peek().type == "IDENT":
                                    mk_parts.append(self.advance().value)
                                else:
                                    break
                            mk_key = ":".join(mk_parts)
                            self.expect("EQUALS")
                            mk_val = self.parse_value_rest()
                            if mk_key.startswith("match:"):
                                match[mk_key[len("match:"):]] = mk_val
                            else:
                                match[mk_key] = mk_val
                        else:
                            self.advance()
                        self.skip_newlines()
                    self.expect("BLOCK_CLOSE")
                else:
                    self.expect("EQUALS")
                    val = self.parse_value_rest()

                    if key == "name":
                        name = val
                    elif key.startswith("match:"):
                        match[key[len("match:"):]] = val
                    else:
                        effects[key] = [val]
            else:
                self.advance()
            self.skip_newlines()

        self.expect("BLOCK_CLOSE")
        return name, match, effects

    def parse_windowrule(self, is_v2: bool, line: int) -> Union[WindowRule, WindowRuleBlock]:
        if self.peek().type == "BLOCK_OPEN":
            name, match, effects = self._parse_rule_block_body()
            return WindowRuleBlock(is_v2, name, match, effects, line)
        self.expect("EQUALS")
        values = self.parse_comma_values()
        rule = values[0].strip() if values else ""
        match_params = [v.strip() for v in values[1:]]
        return WindowRule(is_v2, rule, match_params, line)

    def parse_exec(self, directive: str, line: int) -> ExecDirective:
        self.expect("EQUALS")
        command = self.parse_line_rest()
        return ExecDirective(directive, command, line)

    def parse_line_rest(self) -> str:
        parts = []
        while self.peek().type not in ("NEWLINE", "EOF", "COMMENT", "BLOCK_CLOSE"):
            if self.peek().type == "DOLLAR":
                self.advance()
                var_t = self.expect("IDENT")
                parts.append("$" + var_t.value)
            else:
                t = self.advance()
                parts.append(t.value)
        return self._join_tokens(parts)

    def parse_animation(self, line: int) -> AnimationDirective:
        self.expect("EQUALS")
        values = self.parse_comma_values()
        name = values[0].strip() if len(values) > 0 else ""
        style = values[1].strip() if len(values) > 1 else ""
        speed = values[2].strip() if len(values) > 2 else "1"
        curve = values[3].strip() if len(values) > 3 else "default"
        return AnimationDirective(name, style, speed, curve, line)

    def parse_bezier(self, line: int) -> BezierDirective:
        self.expect("EQUALS")
        values = self.parse_comma_values()
        name = values[0].strip() if len(values) > 0 else ""
        p1x = values[1].strip() if len(values) > 1 else "0"
        p1y = values[2].strip() if len(values) > 2 else "0"
        p2x = values[3].strip() if len(values) > 3 else "1"
        p2y = values[4].strip() if len(values) > 4 else "1"
        return BezierDirective(name, p1x, p1y, p2x, p2y, line)

    def parse_env(self, line: int) -> EnvDirective:
        self.expect("EQUALS")
        name_t = self.expect("IDENT")
        name = name_t.value.strip()
        val = ""
        if self.peek().type == "COMMA":
            self.advance()
            val = self.parse_line_rest()
        return EnvDirective(name, val, line)

    def parse_source(self, line: int) -> SourceDirective:
        self.expect("EQUALS")
        values = self.parse_comma_values()
        path = values[0].strip() if values else ""
        return SourceDirective(path, line)

    def parse_gesture(self, line: int) -> GestureDirective:
        self.skip_newlines()
        self.expect("BLOCK_OPEN")
        body = []
        self.skip_newlines()
        while self.peek().type not in ("BLOCK_CLOSE", "EOF"):
            t = self.peek()
            if t.type == "COMMENT":
                body.append(Comment(t.value, t.line))
                self.advance()
            elif t.type == "IDENT":
                key_t = self.advance()
                self.expect("EQUALS")
                val = self.parse_value_rest()
                body.append(Directive(key_t.value, [val], key_t.line, 0))
            else:
                self.advance()
            self.skip_newlines()
        self.expect("BLOCK_CLOSE")
        return GestureDirective(body, line)

    def parse_device(self, name: str, line: int) -> DeviceSection:
        self.skip_newlines()
        self.expect("BLOCK_OPEN")
        body = []
        self.skip_newlines()
        while self.peek().type not in ("BLOCK_CLOSE", "EOF"):
            t = self.peek()
            if t.type == "COMMENT":
                body.append(Comment(t.value, t.line))
                self.advance()
            elif t.type == "IDENT":
                key_t = self.advance()
                self.expect("EQUALS")
                val = self.parse_value_rest()
                body.append(Directive(key_t.value, [val], key_t.line, 0))
            else:
                self.advance()
            self.skip_newlines()
        self.expect("BLOCK_CLOSE")
        return DeviceSection(name, body, line)

    def parse_workspace(self, line: int) -> WorkspaceDirective:
        self.expect("EQUALS")
        values = self.parse_comma_values()
        name = values[0].strip() if values else ""
        params = [v.strip() for v in values[1:]]
        return WorkspaceDirective(name, params, line)

    def parse_layerrule(self, line: int) -> Union[LayerRuleDirective, LayerRuleBlock]:
        if self.peek().type == "BLOCK_OPEN":
            name, match, effects = self._parse_rule_block_body()
            return LayerRuleBlock(name, match, effects, line)
        self.expect("EQUALS")
        values = self.parse_comma_values()
        rule = values[0].strip() if values else ""
        namespace = values[1].strip() if len(values) > 1 else ""
        return LayerRuleDirective(rule, namespace, line)

    def parse_submap(self, line: int) -> Directive:
        self.expect("EQUALS")
        values = self.parse_comma_values()
        return Directive("submap", values, line, 0)


def parse_config(source: str) -> ConfigFile:
    from hyprconf2lua.lexer import tokenize
    tokens = tokenize(source)
    parser = Parser(tokens)
    return parser.parse()
