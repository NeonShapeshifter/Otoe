from __future__ import annotations

import re
from collections.abc import Callable
from html import escape
from typing import Any

from .mount import FakeWidget, MountedNode, root_widget
from .style import StyleSheet, merge_inline_styles


_HTML_ATTRIBUTE_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]*$")


def render_html(
    target: FakeWidget | MountedNode,
    *,
    pretty: bool = False,
    indent: int = 0,
    attributes: Callable[[FakeWidget], dict[str, Any]] | None = None,
    stylesheet: StyleSheet | None = None,
    strict_styles: bool = True,
) -> str:
    widget = root_widget(target) if isinstance(target, MountedNode) else target
    return _render_widget(
        widget,
        pretty=pretty,
        indent=indent,
        attributes=attributes,
        stylesheet=stylesheet,
        strict_styles=strict_styles,
    )


def _render_widget(
    widget: FakeWidget,
    *,
    pretty: bool,
    indent: int,
    attributes: Callable[[FakeWidget], dict[str, Any]] | None,
    stylesheet: StyleSheet | None,
    strict_styles: bool,
) -> str:
    name = widget.name
    if name == "Text":
        return _inline(
            pretty,
            indent,
            _element(
                "span",
                _widget_attrs(
                    widget,
                    {"class": _classes("otoe-text", widget.props.get("className"))},
                    attributes,
                    stylesheet,
                    strict_styles,
                ),
                escape(str(widget.props.get("content", ""))),
            ),
        )
    if name == "Button":
        attrs = {
            "class": _classes("otoe-button", widget.props.get("className")),
            "type": "button",
        }
        if widget.props.get("disabled"):
            attrs["disabled"] = "disabled"
        if widget.children:
            children = [
                _render_widget(
                    child,
                    pretty=pretty,
                    indent=indent + 2,
                    attributes=attributes,
                    stylesheet=stylesheet,
                    strict_styles=strict_styles,
                )
                for child in widget.children
            ]
            return _block(
                "button",
                _widget_attrs(
                    widget,
                    attrs,
                    attributes,
                    stylesheet,
                    strict_styles,
                ),
                children,
                pretty,
                indent,
            )
        return _inline(
            pretty,
            indent,
            _element(
                "button",
                _widget_attrs(
                    widget,
                    attrs,
                    attributes,
                    stylesheet,
                    strict_styles,
                ),
                escape(str(widget.props.get("label", ""))),
            ),
        )
    if name == "Input":
        attrs = {
            "class": _classes("otoe-input", widget.props.get("className")),
            "placeholder": widget.props.get("placeholder", ""),
            "value": widget.props.get("value", ""),
        }
        if widget.props.get("disabled"):
            attrs["disabled"] = "disabled"
        if widget.props.get("autoFocus"):
            attrs["autofocus"] = "autofocus"
            attrs["data-otoe-autofocus"] = "true"
        return _inline(
            pretty,
            indent,
            _void_element(
                "input",
                _widget_attrs(
                    widget,
                    attrs,
                    attributes,
                    stylesheet,
                    strict_styles,
                ),
            ),
        )
    if name == "VStack":
        return _container(
            "div",
            widget,
            "otoe-stack otoe-vstack",
            pretty,
            indent,
            attributes,
            stylesheet,
            strict_styles,
        )
    if name == "HStack":
        return _container(
            "div",
            widget,
            "otoe-stack otoe-hstack",
            pretty,
            indent,
            attributes,
            stylesheet,
            strict_styles,
        )
    if name == "Panel":
        title = widget.props.get("title")
        children = []
        if title:
            children.append(
                _inline(
                    pretty,
                    indent + 2,
                    _element(
                        "div",
                        {"class": "otoe-panel-title"},
                        escape(str(title)),
                    ),
                )
            )
        children.extend(
            _render_widget(
                child,
                pretty=pretty,
                indent=indent + 2,
                attributes=attributes,
                stylesheet=stylesheet,
                strict_styles=strict_styles,
            )
            for child in widget.children
        )
        return _block(
            "section",
            _widget_attrs(
                widget,
                {
                    "class": _classes("otoe-panel", widget.props.get("className")),
                    **_style_vars(widget),
                },
                attributes,
                stylesheet,
                strict_styles,
            ),
            children,
            pretty,
            indent,
        )
    if name == "ScrollView":
        return _container(
            "div",
            widget,
            "otoe-scroll",
            pretty,
            indent,
            attributes,
            stylesheet,
            strict_styles,
        )
    if name == "ShortcutScope":
        return _container(
            "div",
            widget,
            "otoe-shortcut-scope",
            pretty,
            indent,
            attributes,
            stylesheet,
            strict_styles,
        )
    if name == "FocusScope":
        focus_attrs = {}
        if widget.props.get("trapFocus"):
            focus_attrs["data-otoe-focus-scope"] = "trap"
        if widget.props.get("restoreFocus"):
            focus_attrs["data-otoe-restore-focus"] = "true"
        return _container(
            "div",
            widget,
            "otoe-focus-scope",
            pretty,
            indent,
            attributes,
            stylesheet,
            strict_styles,
            extra_attrs=focus_attrs,
        )
    if name in {"Show", "For"}:
        return _container(
            "div",
            widget,
            f"otoe-fragment otoe-{name.lower()}",
            pretty,
            indent,
            attributes,
            stylesheet,
            strict_styles,
        )
    return _container(
        "div",
        widget,
        f"otoe-widget otoe-{name.lower()}",
        pretty,
        indent,
        attributes,
        stylesheet,
        strict_styles,
    )


def _container(
    tag: str,
    widget: FakeWidget,
    base_class: str,
    pretty: bool,
    indent: int,
    attributes: Callable[[FakeWidget], dict[str, Any]] | None,
    stylesheet: StyleSheet | None,
    strict_styles: bool,
    *,
    extra_attrs: dict[str, Any] | None = None,
) -> str:
    base_attrs = {
        "class": _classes(base_class, widget.props.get("className")),
        **_style_vars(widget),
    }
    if extra_attrs:
        base_attrs.update(extra_attrs)
    return _block(
        tag,
        _widget_attrs(
            widget,
            base_attrs,
            attributes,
            stylesheet,
            strict_styles,
        ),
        [
            _render_widget(
                child,
                pretty=pretty,
                indent=indent + 2,
                attributes=attributes,
                stylesheet=stylesheet,
                strict_styles=strict_styles,
            )
            for child in widget.children
        ],
        pretty,
        indent,
    )


def _widget_attrs(
    widget: FakeWidget,
    base_attrs: dict[str, Any],
    attributes: Callable[[FakeWidget], dict[str, Any]] | None,
    stylesheet: StyleSheet | None,
    strict_styles: bool,
) -> dict[str, Any]:
    attrs = dict(base_attrs)
    if widget.props.get("id"):
        attrs["id"] = widget.props["id"]
    if stylesheet is not None:
        attrs["style"] = merge_inline_styles(
            attrs.get("style"),
            stylesheet.inline_style(
                widget.props.get("className"),
                strict=strict_styles,
            ),
        )
    if attributes is not None:
        attrs.update(attributes(widget))
    return attrs


def _style_vars(widget: FakeWidget) -> dict[str, str]:
    styles = []
    if "gap" in widget.props:
        styles.append(f"--otoe-gap:{_css_size(widget.props['gap'])}")
    if "padding" in widget.props:
        styles.append(f"--otoe-padding:{_css_size(widget.props['padding'])}")
    return {"style": ";".join(styles)} if styles else {}


def _css_size(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{value}px"
    return str(value)


def _classes(base: str, extra: Any) -> str:
    if not extra:
        return base
    return f"{base} {extra}"


def _element(tag: str, attrs: dict[str, Any], body: str) -> str:
    return f"<{tag}{_attrs(attrs)}>{body}</{tag}>"


def _block(
    tag: str,
    attrs: dict[str, Any],
    children: list[str],
    pretty: bool,
    indent: int,
) -> str:
    if not pretty:
        return _element(tag, attrs, "".join(children))

    pad = " " * indent
    if not children:
        return f"{pad}<{tag}{_attrs(attrs)}></{tag}>"
    body = "\n".join(children)
    return f"{pad}<{tag}{_attrs(attrs)}>\n{body}\n{pad}</{tag}>"


def _inline(pretty: bool, indent: int, html: str) -> str:
    if not pretty:
        return html
    return f"{' ' * indent}{html}"


def _void_element(tag: str, attrs: dict[str, Any]) -> str:
    return f"<{tag}{_attrs(attrs)}>"


def _attrs(attrs: dict[str, Any]) -> str:
    parts = []
    for key, value in attrs.items():
        key = _valid_attribute_name(key)
        if value is None or value is False or value == "":
            continue
        parts.append(f'{key}="{escape(str(value), quote=True)}"')
    return (" " + " ".join(parts)) if parts else ""


def _valid_attribute_name(name: object) -> str:
    if not isinstance(name, str):
        raise TypeError(
            f"HTML attribute names must be strings, got {type(name).__name__}."
        )
    if not _HTML_ATTRIBUTE_NAME_RE.fullmatch(name):
        raise ValueError(f"Invalid HTML attribute name {name!r}.")
    return name
