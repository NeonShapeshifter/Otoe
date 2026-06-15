from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any

from .node import Node, create_node
from .widgets import Button, HStack, Input, Panel, ScrollView, Text, VStack


DEFAULT_TAGS = {
    "Button": Button,
    "HStack": HStack,
    "Input": Input,
    "Panel": Panel,
    "ScrollView": ScrollView,
    "Text": Text,
    "VStack": VStack,
}


class TemplateError(ValueError):
    pass


def template(
    source: str,
    *,
    scope: dict[str, Any] | None = None,
    tags: dict[str, Any] | None = None,
) -> Node:
    parser = _TemplateParser(
        scope=scope or {},
        tags=_tag_aliases({**DEFAULT_TAGS, **(tags or {})}),
    )
    parser.feed(source)
    parser.close()
    return parser.finish()


@dataclass
class _Frame:
    tag_name: str
    tag: Any
    props: dict[str, Any]
    children: list[Node | Any] = field(default_factory=list)


class _TemplateParser(HTMLParser):
    def __init__(self, *, scope: dict[str, Any], tags: dict[str, Any]):
        super().__init__(convert_charrefs=True)
        self.scope = scope
        self.tags = tags
        self.stack: list[_Frame] = []
        self.roots: list[Node] = []

    def handle_starttag(self, tag_name: str, attrs: list[tuple[str, str | None]]) -> None:
        self.stack.append(
            _Frame(
                tag_name=tag_name,
                tag=self._tag(tag_name),
                props=self._props(attrs),
            )
        )

    def handle_startendtag(
        self,
        tag_name: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        node = create_node(self._tag(tag_name), **self._props(attrs))
        self._append(node)

    def handle_endtag(self, tag_name: str) -> None:
        if not self.stack:
            raise TemplateError(f"Unexpected closing tag </{tag_name}>.")
        frame = self.stack.pop()
        if frame.tag_name != tag_name:
            raise TemplateError(
                f"Expected closing tag </{frame.tag_name}>; got </{tag_name}>."
            )
        node = self._node_from_frame(frame)
        self._append(node)

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if not text:
            return
        value = self._value(text)
        if self.stack and getattr(self.stack[-1].tag, "primary_prop", None):
            self.stack[-1].children.append(value)
            return
        self._append(Text(value))

    def finish(self) -> Node:
        if self.stack:
            frame = self.stack[-1]
            raise TemplateError(f"Unclosed tag <{frame.tag_name}>.")
        if len(self.roots) != 1:
            raise TemplateError(f"Template must have exactly one root; got {len(self.roots)}.")
        return self.roots[0]

    def _append(self, node: Node) -> None:
        if self.stack:
            self.stack[-1].children.append(node)
        else:
            self.roots.append(node)

    def _tag(self, name: str) -> Any:
        if name not in self.tags:
            raise TemplateError(f"Unknown template tag <{name}>.")
        return self.tags[name]

    def _props(self, attrs: list[tuple[str, str | None]]) -> dict[str, Any]:
        props = {}
        for name, raw_value in attrs:
            props[_prop_name(name)] = True if raw_value is None else self._value(raw_value)
        return props

    def _value(self, raw_value: str) -> Any:
        value = raw_value.strip()
        if value.startswith("{") and value.endswith("}"):
            key = value[1:-1].strip()
            if key not in self.scope:
                raise TemplateError(f"Unknown template expression {{{key}}}.")
            return self.scope[key]
        if value == "true":
            return True
        if value == "false":
            return False
        if value == "none":
            return None
        if value.isdigit():
            return int(value)
        return raw_value

    def _node_from_frame(self, frame: _Frame) -> Node:
        primary_prop = getattr(frame.tag, "primary_prop", None)
        if primary_prop:
            primary_values = [child for child in frame.children if not isinstance(child, Node)]
            child_nodes = tuple(child for child in frame.children if isinstance(child, Node))
            if primary_prop in frame.props:
                if primary_values:
                    raise TemplateError(
                        f"<{frame.tag_name}> received primary content while "
                        f"{primary_prop!r} was passed explicitly."
                    )
                return Node(tag=frame.tag, props=frame.props, children=child_nodes)
            if not frame.children:
                return create_node(frame.tag, **frame.props)
            if primary_values and not child_nodes:
                return create_node(
                    frame.tag,
                    _primary_text_value(primary_values),
                    **frame.props,
                )
            raise TemplateError(
                f"<{frame.tag_name}> cannot mix primary content with child nodes; "
                f"pass {primary_prop!r} explicitly when nesting nodes."
            )
        children = [child for child in frame.children if isinstance(child, Node)]
        return create_node(frame.tag, *children, **frame.props)


def _tag_aliases(tags: dict[str, Any]) -> dict[str, Any]:
    aliases = {}
    for name, tag in tags.items():
        aliases[name] = tag
        aliases[name.lower()] = tag
    return aliases


def _prop_name(name: str) -> str:
    aliases = {
        "classname": "className",
        "onclick": "onClick",
        "onchange": "onChange",
        "onfocus": "onFocus",
        "onblur": "onBlur",
        "onkeydown": "onKeyDown",
    }
    return aliases.get(name, name)


def _primary_text_value(values: list[Any]) -> Any:
    if len(values) == 1:
        return values[0]
    if all(isinstance(value, str) for value in values):
        return "".join(values)
    raise TemplateError("Primary template content cannot mix expression values.")
