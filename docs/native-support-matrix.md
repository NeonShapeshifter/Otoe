# Native Support Matrix

Status: experimental/headless evidence, not production renderer.

This matrix records what the current `native-python` path can prove through
deterministic layout, paint, input, and PNG tests. It is validated from the
internal widget registry, style schema, and capability profile:

- `src/otoe/_widget_contracts.py`
- `src/otoe/_style_schema.py`
- `src/otoe/capabilities.py`

It does not promise a production desktop renderer, GPU backend, platform
accessibility tree, or browser CSS parity.

## Widget And Control Support

Unlisted custom widgets fall back to container layout when their mounted
children can be laid out. `Show` and `For` are control nodes, not registry
widgets; native layout sees the mounted branch or repeated children.

| Widget/control | Source | Native role | Primary prop | Events |
| --- | --- | --- | --- | --- |
| `Text` | core widget | `text` | `content` | - |
| `Button` | core widget | `control` | `label` | `onBlur`, `onClick`, `onFocus`, `onKeyDown` |
| `Input` | core widget | `control` | - | `onBlur`, `onChange`, `onFocus`, `onKeyDown` |
| `VStack` | core widget | `container` | - | - |
| `HStack` | core widget | `container` | - | - |
| `Panel` | core widget | `container` | - | - |
| `ScrollView` | core widget | `container` | - | `onScroll` |
| `ShortcutScope` | core widget | `container` | - | `onGlobalKeyDown` |
| `FocusScope` | core widget | `container` | - | - |
| `Show` | control node | `container` | - | resolved by mount/control-flow |
| `For` | control node | `container` | - | resolved by mount/control-flow |

## Input Support

Supported means covered by current `NativeSurface` or `NativeWindowDriver`
evidence. Deferred means intentionally named as future work, not silently
missing.

| Input/event | Status |
| --- | --- |
| `caret_movement` | `deferred` |
| `click` | `supported` |
| `drag` | `deferred` |
| `focus` | `supported` |
| `gesture` | `deferred` |
| `ime` | `deferred` |
| `inertial_scroll` | `deferred` |
| `input_text` | `supported` |
| `key_down` | `supported` |
| `key_input` | `supported` |
| `pointer_move` | `deferred` |
| `shortcut` | `supported` |
| `tab_focus` | `supported` |
| `text_selection` | `deferred` |
| `uncontrolled_input` | `deferred` |
| `wheel` | `supported` |

## Style Support

`layout` affects native geometry, `paint` affects paint commands, `layout+paint`
affects both, and `ignored` is accepted for artifact/HTML compatibility but has
no current native effect.

| Internal prop | CSS prop | Value kind | Native support |
| --- | --- | --- | --- |
| `alignItems` | `align-items` | `keyword` | `layout` |
| `background` | `background` | `color-token` | `paint` |
| `borderColor` | `border-color` | `color-token` | `paint` |
| `borderRadius` | `border-radius` | `dimension` | `paint` |
| `borderStyle` | `border-style` | `keyword` | `ignored` |
| `borderWidth` | `border-width` | `dimension` | `layout+paint` |
| `color` | `color` | `color-token` | `paint` |
| `display` | `display` | `keyword` | `ignored` |
| `fontSize` | `font-size` | `dimension` | `layout+paint` |
| `fontWeight` | `font-weight` | `number-keyword` | `ignored` |
| `gap` | `gap` | `dimension` | `layout` |
| `height` | `height` | `dimension` | `layout` |
| `justifyContent` | `justify-content` | `keyword` | `layout` |
| `margin` | `margin` | `dimension` | `ignored` |
| `maxHeight` | `max-height` | `dimension` | `layout` |
| `maxWidth` | `max-width` | `dimension` | `layout` |
| `minHeight` | `min-height` | `dimension` | `layout` |
| `minWidth` | `min-width` | `dimension` | `layout` |
| `opacity` | `opacity` | `number-keyword` | `ignored` |
| `overflow` | `overflow` | `keyword` | `paint` |
| `padding` | `padding` | `dimension` | `layout` |
| `scrollY` | - | `dimension` | `layout` |
| `textOverflow` | `text-overflow` | `keyword` | `paint` |
| `whiteSpace` | `white-space` | `keyword` | `paint` |
| `width` | `width` | `dimension` | `layout` |

## Renderer Boundaries

These are the current backend coverage boundaries declared by the native
capability profile.

| Boundary | Status |
| --- | --- |
| `paint` | `supported` |
| `renderTreeLayout` | `supported` |
