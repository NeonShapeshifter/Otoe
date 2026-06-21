from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from functools import lru_cache
from types import MappingProxyType
from typing import cast

from .events import EventSignature


_EMPTY_EVENT_SIGNATURES: Mapping[str, EventSignature] = MappingProxyType({})


@dataclass(frozen=True)
class WidgetContract:
    name: str
    widget: type
    props: frozenset[str]
    events: frozenset[str]
    event_signatures: Mapping[str, EventSignature]
    primary_prop: str | None


@dataclass(frozen=True)
class _WidgetContractSpec:
    props: frozenset[str]
    events: frozenset[str] = frozenset()
    event_signatures: Mapping[str, EventSignature] = field(
        default_factory=lambda: _EMPTY_EVENT_SIGNATURES
    )
    primary_prop: str | None = None


_CORE_WIDGET_SPECS: Mapping[str, _WidgetContractSpec] = MappingProxyType(
    {
        "Text": _WidgetContractSpec(
            props=frozenset({"content", "className", "color", "id"}),
            primary_prop="content",
        ),
        "Button": _WidgetContractSpec(
            props=frozenset({"label", "className", "disabled", "id"}),
            events=frozenset({"onClick", "onKeyDown", "onFocus", "onBlur"}),
            event_signatures=MappingProxyType(
                {
                    "onBlur": EventSignature(),
                    "onClick": EventSignature(),
                    "onFocus": EventSignature(),
                    "onKeyDown": EventSignature(("key",)),
                }
            ),
            primary_prop="label",
        ),
        "Input": _WidgetContractSpec(
            props=frozenset(
                {"value", "placeholder", "className", "disabled", "autoFocus", "id"}
            ),
            events=frozenset({"onChange", "onKeyDown", "onFocus", "onBlur"}),
            event_signatures=MappingProxyType(
                {
                    "onBlur": EventSignature(),
                    "onChange": EventSignature(("value",)),
                    "onFocus": EventSignature(),
                    "onKeyDown": EventSignature(("key",)),
                }
            ),
        ),
        "VStack": _WidgetContractSpec(
            props=frozenset({"className", "gap", "padding", "id"}),
        ),
        "HStack": _WidgetContractSpec(
            props=frozenset({"className", "gap", "padding", "id"}),
        ),
        "Panel": _WidgetContractSpec(
            props=frozenset({"className", "title", "id"}),
        ),
        "ScrollView": _WidgetContractSpec(
            props=frozenset({"className", "id", "scrollY"}),
            events=frozenset({"onScroll"}),
            event_signatures=MappingProxyType(
                {
                    "onScroll": EventSignature(("next_scroll_y",)),
                }
            ),
        ),
        "ShortcutScope": _WidgetContractSpec(
            props=frozenset({"className", "id"}),
            events=frozenset({"onGlobalKeyDown"}),
            event_signatures=MappingProxyType(
                {
                    "onGlobalKeyDown": EventSignature(("event",)),
                }
            ),
        ),
        "FocusScope": _WidgetContractSpec(
            props=frozenset({"className", "trapFocus", "restoreFocus", "id"}),
        ),
    }
)


def widget_contract_for_tag(tag: object) -> WidgetContract | None:
    if not isinstance(tag, type):
        return None
    return _registry_by_tag().get(tag)


def widget_contract_for_name(name: str) -> WidgetContract | None:
    return _registry_by_name().get(name)


def known_widget_names() -> tuple[str, ...]:
    return tuple(_CORE_WIDGET_SPECS)


def widget_props(tag: object) -> frozenset[str]:
    contract = widget_contract_for_tag(tag)
    if contract is not None:
        return contract.props
    return frozenset(getattr(tag, "props", ()))


def widget_events(tag: object) -> frozenset[str]:
    contract = widget_contract_for_tag(tag)
    if contract is not None:
        return contract.events
    return frozenset(getattr(tag, "events", ()))


def widget_event_signatures(tag: object) -> Mapping[str, EventSignature]:
    contract = widget_contract_for_tag(tag)
    if contract is not None:
        return contract.event_signatures
    signatures = getattr(tag, "event_signatures", _EMPTY_EVENT_SIGNATURES)
    if not isinstance(signatures, Mapping):
        return _EMPTY_EVENT_SIGNATURES
    return cast(Mapping[str, EventSignature], signatures)


def _core_widget_props(name: str) -> set[str]:
    return set(_core_widget_spec(name).props)


def _core_widget_events(name: str) -> set[str]:
    return set(_core_widget_spec(name).events)


def _core_widget_event_signatures(name: str) -> dict[str, EventSignature]:
    return dict(_core_widget_spec(name).event_signatures)


def _core_widget_primary_prop(name: str) -> str | None:
    return _core_widget_spec(name).primary_prop


def _core_widget_spec(name: str) -> _WidgetContractSpec:
    return _CORE_WIDGET_SPECS[name]


@lru_cache(maxsize=1)
def _registry_by_name() -> Mapping[str, WidgetContract]:
    from . import widgets

    contracts: dict[str, WidgetContract] = {}
    for name, spec in _CORE_WIDGET_SPECS.items():
        contracts[name] = WidgetContract(
            name=name,
            widget=getattr(widgets, name),
            props=spec.props,
            events=spec.events,
            event_signatures=MappingProxyType(dict(spec.event_signatures)),
            primary_prop=spec.primary_prop,
        )
    return MappingProxyType(contracts)


@lru_cache(maxsize=1)
def _registry_by_tag() -> Mapping[type, WidgetContract]:
    return MappingProxyType(
        {contract.widget: contract for contract in _registry_by_name().values()}
    )
