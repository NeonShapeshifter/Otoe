from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from ._native_shared import native_style_support


STYLE_IR_SCHEMA_VERSION = 1
STYLE_OPS_SCHEMA_VERSION = 1
STYLE_OPS_FORMAT = "otoe-style-ops"


class StyleIRError(ValueError):
    pass


@dataclass(frozen=True)
class StyleOpsClassReplay:
    class_name: str
    selector: str
    missing: bool
    applied_declarations: dict[str, Any]
    omitted_ops: tuple[dict[str, Any], ...]
    errors: tuple[str, ...]


@dataclass(frozen=True)
class StyleOpsDirectReplay:
    path: tuple[int, ...]
    widget: str
    applied_declarations: dict[str, Any]
    omitted_ops: tuple[dict[str, Any], ...]
    errors: tuple[str, ...]


@dataclass(frozen=True)
class StyleIRArtifact:
    payload: dict[str, Any]
    style_ops: dict[str, Any]
    rules: tuple[dict[str, Any], ...]
    direct_styles: tuple[dict[str, Any], ...]
    rules_by_class: dict[str, dict[str, Any]]
    direct_styles_by_path: dict[tuple[int, ...], dict[str, Any]]
    style_support: dict[str, str]

    @property
    def schema_version(self) -> Any:
        return self.payload.get("schemaVersion")

    @property
    def style_ops_schema_version(self) -> Any:
        return self.style_ops.get("schemaVersion")

    @property
    def style_ops_format(self) -> Any:
        return self.style_ops.get("format")

    @property
    def backend(self) -> Any:
        return self.payload.get("backend")


@dataclass(frozen=True)
class AppliedStyleOps:
    classes: tuple[StyleOpsClassReplay, ...]
    direct_styles: tuple[StyleOpsDirectReplay, ...]
    errors: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return (
            not self.errors
            and all(class_replay.errors == () for class_replay in self.classes)
            and all(
                direct_style_replay.errors == ()
                for direct_style_replay in self.direct_styles
            )
        )

    @property
    def classes_by_name(self) -> dict[str, StyleOpsClassReplay]:
        return {
            class_replay.class_name: class_replay
            for class_replay in self.classes
            if class_replay.class_name != "<invalid>"
        }

    @property
    def direct_styles_by_path(self) -> dict[tuple[int, ...], StyleOpsDirectReplay]:
        return {
            direct_style_replay.path: direct_style_replay
            for direct_style_replay in self.direct_styles
        }


@dataclass(frozen=True)
class StyleOpsValidation:
    applied: AppliedStyleOps
    errors: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.errors


def load_style_ir(payload: Mapping[str, Any]) -> StyleIRArtifact:
    if not isinstance(payload, Mapping):
        raise StyleIRError("style artifact must be a JSON object")
    _require_schema_version(payload, "style artifact", STYLE_IR_SCHEMA_VERSION)

    style_ops = payload.get("styleOps")
    if not isinstance(style_ops, dict):
        raise StyleIRError("style artifact is missing object styleOps")
    _require_schema_version(style_ops, "styleOps", STYLE_OPS_SCHEMA_VERSION)
    if style_ops.get("format") != STYLE_OPS_FORMAT:
        raise StyleIRError(
            f"styleOps format must be {STYLE_OPS_FORMAT!r}; "
            f"got {style_ops.get('format')!r}"
        )

    rules = _require_payload_list(payload, "rules", default=())
    direct_styles = _require_payload_list(payload, "directStyles", default=())
    classes = _require_payload_list(style_ops, "classes", default=(), label="styleOps")
    direct_style_ops = _require_payload_list(
        style_ops,
        "directStyles",
        default=(),
        label="styleOps",
    )
    normalized_style_ops = dict(style_ops)
    normalized_style_ops["classes"] = list(classes)
    normalized_style_ops["directStyles"] = list(direct_style_ops)

    return StyleIRArtifact(
        payload=dict(payload),
        style_ops=normalized_style_ops,
        rules=tuple(rules),
        direct_styles=tuple(direct_styles),
        rules_by_class=_rules_by_class(rules),
        direct_styles_by_path=_direct_styles_by_path(direct_styles),
        style_support=style_ops_support_map(normalized_style_ops),
    )


def apply_style_ops(
    artifact: StyleIRArtifact | Mapping[str, Any],
) -> AppliedStyleOps:
    style_ir = (
        artifact
        if isinstance(artifact, StyleIRArtifact)
        else load_style_ir(artifact)
    )
    class_replays = tuple(
        replay_style_ops_class(class_payload, style_support=style_ir.style_support)
        for class_payload in style_ir.style_ops["classes"]
    )
    direct_style_replays = tuple(
        replay_style_ops_direct(
            direct_style_payload,
            style_support=style_ir.style_support,
        )
        for direct_style_payload in style_ir.style_ops["directStyles"]
    )
    errors = _duplicate_style_ops_errors(class_replays, direct_style_replays)
    return AppliedStyleOps(
        classes=class_replays,
        direct_styles=direct_style_replays,
        errors=errors,
    )


def validate_style_ops(
    artifact: StyleIRArtifact | Mapping[str, Any],
) -> StyleOpsValidation:
    style_ir = (
        artifact
        if isinstance(artifact, StyleIRArtifact)
        else load_style_ir(artifact)
    )
    applied = apply_style_ops(style_ir)
    errors: list[str] = [
        *applied.errors,
        *(
            error
            for replay in applied.classes
            for error in replay.errors
        ),
        *(
            error
            for replay in applied.direct_styles
            for error in replay.errors
        ),
    ]
    errors.extend(_validate_class_style_ops(style_ir, applied))
    errors.extend(_validate_direct_style_ops(style_ir, applied))
    return StyleOpsValidation(applied=applied, errors=tuple(errors))


def style_ops_support_map(style_ops: dict[str, Any]) -> dict[str, str]:
    capabilities = style_ops.get("capabilities")
    if not isinstance(capabilities, dict):
        return {}
    styles = capabilities.get("styles")
    if not isinstance(styles, dict):
        return {}
    return {
        property_name: support
        for property_name, support in styles.items()
        if isinstance(property_name, str) and isinstance(support, str)
    }


def style_op_support(
    property_name: Any,
    style_support: Mapping[str, str] | None,
) -> str:
    if not isinstance(property_name, str):
        return "unsupported"
    if style_support is not None and property_name in style_support:
        return style_support[property_name]
    return native_style_support(property_name) or "unsupported"


def replay_style_ops_class(
    class_payload: Any,
    *,
    style_support: Mapping[str, str] | None = None,
) -> StyleOpsClassReplay:
    if not isinstance(class_payload, dict):
        return StyleOpsClassReplay(
            class_name="<invalid>",
            selector="",
            missing=False,
            applied_declarations={},
            omitted_ops=(),
            errors=("styleOps class entry must be an object",),
        )

    errors: list[str] = []
    class_name = class_payload.get("className")
    if not isinstance(class_name, str):
        class_name = "<invalid>"
        errors.append("styleOps className must be a string")
    selector = class_payload.get("selector")
    if not isinstance(selector, str):
        selector = ""
        errors.append("styleOps selector must be a string")
    missing = class_payload.get("missing")
    if not isinstance(missing, bool):
        missing = False
        errors.append("styleOps missing must be a boolean")

    applied_declarations = _replay_set_style_ops(
        class_name,
        class_payload.get("ops", []),
        errors,
        style_support,
    )
    omitted_ops = _replay_omitted_style_ops(
        class_name,
        class_payload.get("omittedOps", []),
        errors,
        style_support,
    )

    return StyleOpsClassReplay(
        class_name=class_name,
        selector=selector,
        missing=missing,
        applied_declarations=applied_declarations,
        omitted_ops=omitted_ops,
        errors=tuple(errors),
    )


def replay_style_ops_direct(
    direct_payload: Any,
    *,
    style_support: Mapping[str, str] | None = None,
) -> StyleOpsDirectReplay:
    if not isinstance(direct_payload, dict):
        return StyleOpsDirectReplay(
            path=(),
            widget="<invalid>",
            applied_declarations={},
            omitted_ops=(),
            errors=("styleOps directStyles entry must be an object",),
        )

    errors: list[str] = []
    path = _style_ops_path(direct_payload.get("path"), errors)
    widget = direct_payload.get("widget")
    if not isinstance(widget, str):
        widget = "<invalid>"
        errors.append("styleOps directStyles widget must be a string")

    label = f"direct style {list(path)}"
    applied_declarations = _replay_set_style_ops(
        label,
        direct_payload.get("ops", []),
        errors,
        style_support,
    )
    omitted_ops = _replay_omitted_style_ops(
        label,
        direct_payload.get("omittedOps", []),
        errors,
        style_support,
    )

    return StyleOpsDirectReplay(
        path=path,
        widget=widget,
        applied_declarations=applied_declarations,
        omitted_ops=omitted_ops,
        errors=tuple(errors),
    )


def expected_omitted_style_ops(
    rule_payload: dict[str, Any] | None,
    style_support: Mapping[str, str] | None = None,
) -> tuple[dict[str, Any], ...]:
    if not isinstance(rule_payload, dict):
        return ()
    omitted = rule_payload.get("omittedDeclarations", [])
    if not isinstance(omitted, list):
        return ()
    return tuple(
        {
            "op": "omitStyle",
            "property": declaration.get("property"),
            "support": style_op_support(declaration.get("property"), style_support),
            "status": declaration.get("status"),
            "value": declaration.get("value"),
            "message": declaration.get("message"),
        }
        for declaration in omitted
        if isinstance(declaration, dict)
    )


def _replay_set_style_ops(
    class_name: str,
    ops_payload: Any,
    errors: list[str],
    style_support: Mapping[str, str] | None,
) -> dict[str, Any]:
    if not isinstance(ops_payload, list):
        errors.append(f"styleOps class {class_name!r} ops must be a list")
        return {}

    applied_declarations: dict[str, Any] = {}
    for index, op_payload in enumerate(ops_payload):
        if not isinstance(op_payload, dict):
            errors.append(f"styleOps class {class_name!r} op {index} must be an object")
            continue
        if op_payload.get("op") != "setStyle":
            errors.append(
                f"styleOps class {class_name!r} op {index} must use op='setStyle'"
            )
            continue
        property_name = op_payload.get("property")
        if not isinstance(property_name, str):
            errors.append(
                f"styleOps class {class_name!r} op {index} property must be a string"
            )
            continue
        expected_support = style_op_support(property_name, style_support)
        if op_payload.get("support") != expected_support:
            errors.append(
                f"styleOps class {class_name!r} op {index} support "
                f"{op_payload.get('support')!r} does not match {expected_support!r}"
            )
        value = op_payload.get("value")
        errors.extend(
            _style_value_payload_errors(
                value,
                label=f"styleOps class {class_name!r} op {index} value",
                portable=True,
            )
        )
        applied_declarations[property_name] = value
    return applied_declarations


def _replay_omitted_style_ops(
    class_name: str,
    omitted_ops_payload: Any,
    errors: list[str],
    style_support: Mapping[str, str] | None,
) -> tuple[dict[str, Any], ...]:
    if not isinstance(omitted_ops_payload, list):
        errors.append(f"styleOps class {class_name!r} omittedOps must be a list")
        return ()

    omitted_ops: list[dict[str, Any]] = []
    for index, op_payload in enumerate(omitted_ops_payload):
        if not isinstance(op_payload, dict):
            errors.append(
                f"styleOps class {class_name!r} omitted op {index} must be an object"
            )
            continue
        omitted_ops.append(
            _normalize_style_omitted_op(
                class_name,
                index,
                op_payload,
                errors,
                style_support,
            )
        )
    return tuple(omitted_ops)


def _normalize_style_omitted_op(
    class_name: str,
    index: int,
    op_payload: dict[str, Any],
    errors: list[str],
    style_support: Mapping[str, str] | None,
) -> dict[str, Any]:
    if op_payload.get("op") != "omitStyle":
        errors.append(
            f"styleOps class {class_name!r} omitted op {index} must use op='omitStyle'"
        )
    property_name = op_payload.get("property")
    if not isinstance(property_name, str):
        errors.append(
            f"styleOps class {class_name!r} omitted op {index} property must be a string"
        )
    expected_support = style_op_support(property_name, style_support)
    if op_payload.get("support") != expected_support:
        errors.append(
            f"styleOps class {class_name!r} omitted op {index} support "
            f"{op_payload.get('support')!r} does not match {expected_support!r}"
        )
    value = op_payload.get("value")
    errors.extend(
        _style_value_payload_errors(
            value,
            label=f"styleOps class {class_name!r} omitted op {index} value",
            portable=False,
        )
    )
    return {
        "op": op_payload.get("op"),
        "property": property_name,
        "support": op_payload.get("support"),
        "status": op_payload.get("status"),
        "value": value,
        "message": op_payload.get("message"),
    }


def _style_ops_path(path_payload: Any, errors: list[str]) -> tuple[int, ...]:
    if not isinstance(path_payload, list):
        errors.append("styleOps directStyles path must be a list")
        return ()
    path: list[int] = []
    for index, item in enumerate(path_payload):
        if type(item) is not int or item < 0:
            errors.append(
                f"styleOps directStyles path item {index} must be a non-negative integer"
            )
            continue
        path.append(item)
    return tuple(path)


def _require_schema_version(
    payload: Mapping[str, Any],
    label: str,
    expected: int,
) -> None:
    version = payload.get("schemaVersion")
    if version != expected:
        raise StyleIRError(
            f"{label}: unsupported schemaVersion {version!r}; expected {expected}"
        )


def _require_payload_list(
    payload: Mapping[str, Any],
    key: str,
    *,
    default: tuple[Any, ...],
    label: str = "style artifact",
) -> tuple[Any, ...]:
    value = payload.get(key, list(default))
    if not isinstance(value, list):
        raise StyleIRError(f"{label} {key} must be a list")
    return tuple(value)


def _rules_by_class(rules: tuple[Any, ...]) -> dict[str, dict[str, Any]]:
    return {
        rule["className"]: rule
        for rule in rules
        if isinstance(rule, dict) and isinstance(rule.get("className"), str)
    }


def _direct_styles_by_path(
    direct_styles: tuple[Any, ...],
) -> dict[tuple[int, ...], dict[str, Any]]:
    return {
        path: direct_style
        for direct_style in direct_styles
        if isinstance(direct_style, dict)
        and (path := _payload_path(direct_style.get("path"))) is not None
    }


def _payload_path(path_payload: Any) -> tuple[int, ...] | None:
    if not isinstance(path_payload, list):
        return None
    path: list[int] = []
    for item in path_payload:
        if type(item) is not int or item < 0:
            return None
        path.append(item)
    return tuple(path)


def _duplicate_style_ops_errors(
    class_replays: tuple[StyleOpsClassReplay, ...],
    direct_style_replays: tuple[StyleOpsDirectReplay, ...],
) -> tuple[str, ...]:
    errors: list[str] = []
    seen_classes: set[str] = set()
    for replay in class_replays:
        if replay.class_name == "<invalid>":
            continue
        if replay.class_name in seen_classes:
            errors.append(f"duplicate styleOps class {replay.class_name!r}")
        seen_classes.add(replay.class_name)

    seen_paths: set[tuple[int, ...]] = set()
    for replay in direct_style_replays:
        if replay.path in seen_paths:
            errors.append(
                f"duplicate styleOps directStyles path {list(replay.path)!r}"
            )
        seen_paths.add(replay.path)
    return tuple(errors)


def _validate_class_style_ops(
    style_ir: StyleIRArtifact,
    applied: AppliedStyleOps,
) -> tuple[str, ...]:
    errors: list[str] = []
    seen_classes: set[str] = set()
    for replay in applied.classes:
        if replay.class_name == "<invalid>":
            continue
        seen_classes.add(replay.class_name)
        rule_payload = style_ir.rules_by_class.get(replay.class_name)
        if rule_payload is None:
            errors.append(
                f"styleOps class {replay.class_name!r} is not present in compiled rules"
            )
            continue

        expected_missing = bool(rule_payload.get("missing"))
        expected_declarations = rule_payload.get("declarations", {})
        if not isinstance(expected_declarations, dict):
            expected_declarations = {}
            errors.append(
                f"compiled rule {replay.class_name!r} declarations must be an object"
            )
        else:
            errors.extend(
                _declaration_value_errors(
                    expected_declarations,
                    label=f"compiled rule {replay.class_name!r}",
                    portable=True,
                )
            )
        errors.extend(
            _omitted_declaration_value_errors(
                rule_payload.get("omittedDeclarations", []),
                label=f"compiled rule {replay.class_name!r}",
            )
        )
        expected_omitted_ops = expected_omitted_style_ops(
            rule_payload,
            style_ir.style_support,
        )

        if replay.missing is not expected_missing:
            errors.append(
                f"styleOps class {replay.class_name!r} missing flag does not match compiled rule"
            )
        if replay.applied_declarations != expected_declarations:
            errors.append(
                f"styleOps class {replay.class_name!r} applied declarations do not match compiled rules"
            )
        if replay.omitted_ops != expected_omitted_ops:
            errors.append(
                f"styleOps class {replay.class_name!r} omitted ops do not match compiled rules"
            )

    missing_ops = sorted(set(style_ir.rules_by_class) - seen_classes)
    if missing_ops:
        errors.append(
            "styleOps missing classes from compiled rules: "
            + ", ".join(missing_ops)
        )
    return tuple(errors)


def _validate_direct_style_ops(
    style_ir: StyleIRArtifact,
    applied: AppliedStyleOps,
) -> tuple[str, ...]:
    errors: list[str] = []
    seen_paths: set[tuple[int, ...]] = set()
    for replay in applied.direct_styles:
        seen_paths.add(replay.path)
        expected_payload = style_ir.direct_styles_by_path.get(replay.path)
        if expected_payload is None:
            errors.append(
                f"styleOps directStyles {list(replay.path)!r} is not present in compiled artifact"
            )
            continue

        expected_widget = expected_payload.get("widget")
        expected_declarations = expected_payload.get("declarations", {})
        if not isinstance(expected_declarations, dict):
            expected_declarations = {}
            errors.append(
                f"compiled directStyles {list(replay.path)!r} declarations must be an object"
            )
        else:
            errors.extend(
                _declaration_value_errors(
                    expected_declarations,
                    label=f"compiled directStyles {list(replay.path)!r}",
                    portable=True,
                )
            )
        errors.extend(
            _omitted_declaration_value_errors(
                expected_payload.get("omittedDeclarations", []),
                label=f"compiled directStyles {list(replay.path)!r}",
            )
        )
        expected_omitted_ops = expected_omitted_style_ops(
            expected_payload,
            style_ir.style_support,
        )

        if replay.widget != expected_widget:
            errors.append(
                f"styleOps directStyles {list(replay.path)!r} widget does not match compiled artifact"
            )
        if replay.applied_declarations != expected_declarations:
            errors.append(
                f"styleOps directStyles {list(replay.path)!r} applied declarations do not match compiled artifact"
            )
        if replay.omitted_ops != expected_omitted_ops:
            errors.append(
                f"styleOps directStyles {list(replay.path)!r} omitted ops do not match compiled artifact"
            )

    missing_direct_ops = sorted(set(style_ir.direct_styles_by_path) - seen_paths)
    if missing_direct_ops:
        errors.append(
            "styleOps missing directStyles from compiled artifact: "
            + ", ".join(str(list(path)) for path in missing_direct_ops)
        )
    return tuple(errors)


def _declaration_value_errors(
    declarations: Mapping[str, Any],
    *,
    label: str,
    portable: bool,
) -> tuple[str, ...]:
    errors: list[str] = []
    for property_name, value in declarations.items():
        if not isinstance(property_name, str):
            errors.append(f"{label} declaration property must be a string")
            continue
        errors.extend(
            _style_value_payload_errors(
                value,
                label=f"{label} declaration {property_name!r} value",
                portable=portable,
            )
        )
    return tuple(errors)


def _omitted_declaration_value_errors(
    omitted_declarations: Any,
    *,
    label: str,
) -> tuple[str, ...]:
    if not isinstance(omitted_declarations, list):
        return ()
    errors: list[str] = []
    for index, declaration in enumerate(omitted_declarations):
        if not isinstance(declaration, dict):
            continue
        errors.extend(
            _style_value_payload_errors(
                declaration.get("value"),
                label=f"{label} omitted declaration {index} value",
                portable=False,
            )
        )
    return tuple(errors)


def _style_value_payload_errors(
    value: Any,
    *,
    label: str,
    portable: bool,
) -> tuple[str, ...]:
    if not isinstance(value, dict):
        return (f"{label} must be a serialized style value object",)

    kind = value.get("type")
    if kind == "literal":
        return _literal_style_value_errors(value, label=label)
    if kind == "size":
        return _size_style_value_errors(value, label=label)
    if kind == "token":
        if portable:
            return (f"{label} must be resolved before styleOps runtime",)
        return _token_style_value_errors(value, label=label)
    if kind == "runtime":
        if portable:
            return (f"{label} cannot be a runtime style value",)
        return _runtime_style_value_errors(value, label=label)
    if not isinstance(kind, str):
        return (f"{label} type must be a string",)
    return (f"{label} has unknown serialized style value type {kind!r}",)


def _literal_style_value_errors(
    value: Mapping[str, Any],
    *,
    label: str,
) -> tuple[str, ...]:
    if "value" not in value:
        return (f"{label} literal value is required",)
    literal = value.get("value")
    if literal is None or type(literal) in {str, int, float, bool}:
        return ()
    return (f"{label} literal value must be JSON scalar",)


def _size_style_value_errors(
    value: Mapping[str, Any],
    *,
    label: str,
) -> tuple[str, ...]:
    errors: list[str] = []
    size_value = value.get("value")
    if type(size_value) not in {int, float}:
        errors.append(f"{label} size value must be int or float")
    unit = value.get("unit")
    if not isinstance(unit, str) or not unit:
        errors.append(f"{label} size unit must be a non-empty string")
    return tuple(errors)


def _token_style_value_errors(
    value: Mapping[str, Any],
    *,
    label: str,
) -> tuple[str, ...]:
    token_name = value.get("name")
    if not isinstance(token_name, str) or not token_name:
        return (f"{label} token name must be a non-empty string",)
    return ()


def _runtime_style_value_errors(
    value: Mapping[str, Any],
    *,
    label: str,
) -> tuple[str, ...]:
    errors: list[str] = []
    if not isinstance(value.get("valueType"), str) or not value.get("valueType"):
        errors.append(f"{label} runtime valueType must be a non-empty string")
    if not isinstance(value.get("repr"), str):
        errors.append(f"{label} runtime repr must be a string")
    return tuple(errors)
