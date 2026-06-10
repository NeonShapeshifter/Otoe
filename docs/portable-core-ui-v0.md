# Portable Core UI v0

Portable Core UI v0 is the subset that should be treated as the first
product-facing target for parity across HTML render, live HTML where relevant,
headless native rendering, and native-window driver input.

This matrix is intentionally conservative. It should shrink ambiguity before
more primitives are added.

| Primitive | HTML | Live HTML | Native Headless | Native Window Driver | Status |
| --- | --- | --- | --- | --- | --- |
| `Text` | yes | n/a | yes | n/a | core preview |
| `Button` | yes | click/key events | click/focus/key | click/focus/key | core preview |
| `Input` | yes | change/key/focus | focus/key/text | focus/key/text | core preview |
| `VStack` | yes | n/a | stack layout | n/a | core preview |
| `HStack` | yes | n/a | stack layout | n/a | core preview |
| `Panel` | yes | n/a | basic layout/paint | n/a | core preview |
| `ScrollView` | yes | scroll event shape | clipped paint/hit test/scroll | wheel dispatch | core preview |
| `Card` | yes | n/a | through composed widgets/styles | n/a | product preview |
| `Badge` | yes | n/a | through composed widgets/styles | n/a | product preview |
| `ActionButton` | yes | click | through `Button` behavior | through `Button` behavior | product preview |
| `Tabs`/`TabButton` | yes | click | partial through buttons/layout | partial through buttons/layout | product preview |
| `Dialog` | yes | focus overlay behavior in live path | partial layout/paint | partial focus behavior | experimental UI |
| `ListRow` | yes | n/a | through composed widgets/styles | n/a | product preview |
| `MetricTile` | yes | n/a | through composed widgets/styles | n/a | product preview |
| `AppFrame` | yes | n/a | app-shaped layout smoke | n/a | product preview |

## Acceptance Bar

For a primitive to be considered part of Portable Core UI v0, it should have:

- an HTML render test or preview fixture
- a native layout test when it affects geometry
- a native paint test when it affects visible output
- a native click/key/text/scroll test when it exposes input
- a doc example showing the intended app-authoring shape

## Explicit Non-Goals For v0

- Full browser CSS parity.
- Production desktop windowing.
- Accessibility tree output.
- Complex native text shaping.
- A large component catalog.

Primitives outside the matrix can still exist, but docs should label them as
HTML preview or experimental until the parity bar is met.
