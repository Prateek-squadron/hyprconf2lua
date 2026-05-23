from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union


Value = Union[str, List["Value"]]


@dataclass
class Comment:
    text: str
    line: int

    def __str__(self) -> str:
        return self.text


@dataclass
class Directive:
    key: str
    value: List[str]
    line: int
    col: int


@dataclass
class Section:
    name: str
    body: Block
    line: int


@dataclass
class VariableDef:
    name: str
    value: str
    line: int


@dataclass
class ExecDirective:
    kind: str
    command: str
    line: int


@dataclass
class BindDirective:
    mods: List[str]
    key: str
    dispatcher: str
    params: List[str]
    flags: str
    line: int


@dataclass
class MonitorDirective:
    name: str
    mode: str
    position: str
    scale: str
    line: int
    extra: Dict[str, str] = field(default_factory=dict)


@dataclass
class WindowRule:
    is_v2: bool
    rule: str
    match_params: List[str]
    line: int


@dataclass
class AnimationDirective:
    name: str
    style: str
    speed: str
    curve: str
    line: int


@dataclass
class BezierDirective:
    name: str
    p1x: str
    p1y: str
    p2x: str
    p2y: str
    line: int


@dataclass
class EnvDirective:
    name: str
    value: str
    line: int


@dataclass
class SourceDirective:
    path: str
    line: int


@dataclass
class DeviceSection:
    name: str
    body: List[Directive]
    line: int


@dataclass
class GestureDirective:
    body: List[Directive]
    line: int


@dataclass
class WorkspaceDirective:
    name: str
    params: List[str]
    line: int


@dataclass
class LayerRuleDirective:
    rule: str
    namespace: str
    line: int


@dataclass
class SubmapDef:
    name: str
    body: List[BlockStmt]
    line: int


BlockStmt = Union[
    Directive, Section, VariableDef, ExecDirective, BindDirective,
    MonitorDirective, WindowRule, AnimationDirective, BezierDirective,
    EnvDirective, SourceDirective, DeviceSection, GestureDirective,
    WorkspaceDirective, LayerRuleDirective, SubmapDef, Comment,
]

Block = List[BlockStmt]


@dataclass
class ConfigFile:
    body: Block
