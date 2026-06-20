from pathlib import Path
import re

from otoe import (
    Button,
    HStack,
    Input,
    Panel,
    ScrollView,
    Text,
    VStack,
    mount,
    render_html,
)
from otoe._widget_contracts import known_widget_names, widget_contract_for_name
from otoe.events import format_event_signature
from otoe.experimental.native import layout_native, paint_native
from otoe.ui import FocusScope, ShortcutScope


ROOT = Path(__file__).resolve().parents[1]
WIDGET_CONTRACTS_DOC = ROOT / "WIDGET_CONTRACTS.md"

WIDGET_SAMPLES = {
    "Text": lambda: Text("hello"),
    "Button": lambda: Button("Run", onClick=lambda: None),
    "Input": lambda: Input(value="", placeholder="Type"),
    "VStack": lambda: VStack(Text("child")),
    "HStack": lambda: HStack(Text("child")),
    "Panel": lambda: Panel(Text("child"), title="Panel"),
    "ScrollView": lambda: ScrollView(Text("child")),
    "ShortcutScope": lambda: ShortcutScope(
        Text("child"),
        onKeyDown=lambda event: None,
    ),
    "FocusScope": lambda: FocusScope(Text("child")),
}


def test_widget_renderer_samples_cover_core_registry():
    assert tuple(WIDGET_SAMPLES) == known_widget_names()


def test_widget_contract_docs_match_core_registry():
    documented = _documented_core_widget_contracts()

    assert set(documented) == set(known_widget_names())
    for name in known_widget_names():
        contract = widget_contract_for_name(name)
        assert contract is not None
        row = documented[name]

        assert row["primary_prop"] == (contract.primary_prop or "none")
        assert row["props"] == contract.props
        assert row["events"] == _event_catalog(contract)


def test_widget_contract_event_shapes_match_core_registry():
    documented = _documented_event_shapes()
    expected = {}

    for name in known_widget_names():
        contract = widget_contract_for_name(name)
        assert contract is not None
        for event in contract.events:
            signature = contract.event_signatures.get(event)
            parameters = signature.parameters if signature is not None else ()
            expected[f"{name}.{event}"] = _lambda_handler_shape(parameters)

    assert documented == expected


def test_public_widget_samples_render_across_current_renderers():
    for name, factory in WIDGET_SAMPLES.items():
        mounted = mount(factory())
        html = render_html(mounted)
        layout = layout_native(mounted)
        paint = paint_native(layout)

        assert html, name
        assert layout.boxes, name
        assert paint.commands, name


def _documented_core_widget_contracts():
    rows = {}
    in_table = False
    for line in WIDGET_CONTRACTS_DOC.read_text(encoding="utf-8").splitlines():
        if line.startswith("| Widget | Primary Prop | Data Props | Events |"):
            in_table = True
            continue
        if not in_table:
            continue
        if not line.startswith("|"):
            break
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if cells[0].startswith("---"):
            continue
        widget = _single_code_value(cells[0])
        rows[widget] = {
            "primary_prop": _primary_prop(cells[1]),
            "props": frozenset(re.findall(r"`([^`]+)`", cells[2])),
            "events": frozenset(re.findall(r"`([^`]+)`", cells[3])),
        }
    return rows


def _documented_event_shapes():
    rows = {}
    in_table = False
    for line in WIDGET_CONTRACTS_DOC.read_text(encoding="utf-8").splitlines():
        if line.startswith("| Event | Handler |"):
            in_table = True
            continue
        if not in_table:
            continue
        if not line.startswith("|"):
            break
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if cells[0].startswith("---"):
            continue
        handler_shape = _single_code_value(cells[1])
        for event_name in re.findall(r"`([^`]+)`", cells[0]):
            rows[event_name] = handler_shape
    return rows


def _primary_prop(cell: str) -> str:
    if cell == "none":
        return "none"
    return _single_code_value(cell)


def _single_code_value(cell: str) -> str:
    values = re.findall(r"`([^`]+)`", cell)
    assert len(values) == 1
    return values[0]


def _event_catalog(contract) -> frozenset[str]:
    return frozenset(
        format_event_signature(event, contract.event_signatures.get(event))
        for event in contract.events
    )


def _lambda_handler_shape(parameters: tuple[str, ...]) -> str:
    if not parameters:
        return "lambda: ..."
    return f"lambda {', '.join(parameters)}: ..."
