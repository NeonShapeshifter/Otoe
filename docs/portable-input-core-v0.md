# Portable Input Core v0

Portable Input Core v0 is the smallest input contract Otoe app surfaces should
follow when targeting HTML preview, native/headless tests, and hardware-oriented
interfaces.

It is not a new renderer, gesture layer, accessibility tree, or platform event
API. It is the product contract Otoe examples and appliance-style surfaces
should satisfy so the same interface can be operated with touch, mouse, and
keyboard across the current HTML preview and NativeSurface paths.

## Input Matrix

| Intent          | Mouse        | Touch                                  | Keyboard                   | Live HTML        | NativeSurface    |
|-----------------|--------------|----------------------------------------|----------------------------|------------------|------------------|
| Activate        | click        | tap as click                           | Enter/Space                | supported        | supported        |
| Focus next/prev | click/tab    | tap focus                              | Tab/Shift+Tab              | browser/live     | supported        |
| Text input      | keyboard     | OS keyboard                            | key input                  | supported        | supported        |
| Scroll          | wheel        | browser touch scroll / native deferred | wheel/Page keys deferred   | partial          | wheel supported  |
| Dismiss         | click cancel | tap cancel                             | Escape                     | partial          | partial          |
| Shortcut        | n/a          | n/a                                    | Ctrl/meta/Esc              | supported        | supported        |
| Context action  | right click  | long press                             | Menu/Shift+F10             | planned/deferred | planned/deferred |
| Hover feedback  | hover        | n/a/stylus only                        | focus equivalent           | enhancement      | deferred         |
| Drag/reorder    | drag         | long press drag                        | keyboard fallback required | deferred         | deferred         |

## Platform-Familiar Conventions

- Click and tap activate the visible primary action.
- Enter and Space activate the focused control.
- Tab and Shift+Tab move focus through controls in a predictable order.
- Escape closes dialogs, palettes, menus, contextual panels, and other
  temporary overlays.
- Arrow keys navigate lists, menus, palettes, and roving choices when the
  component owns that pattern.
- Right click, long press, and the keyboard context key or Shift+F10 open
  secondary actions.
- Dangerous actions require confirmation before the effect is committed.

## Context Actions

Touch does have long press, but Otoe should not model long press as hover. Long
press is a contextual intent, equivalent to the familiar secondary-action paths
on desktop systems:

```text
contextAction = right click / long press / keyboard context
```

Portable UI should expose critical primary work without context actions. Context
actions are appropriate for secondary conveniences such as copy ID, pin/unpin,
inspect raw details, export, or advanced diagnostics. Until Otoe has a portable
`onContext` event, examples should include an explicit visible control such as
`...` or `More` for the same secondary actions.

## Explicit Limits

Portable Input Core v0 intentionally does not include:

- gestures,
- multi-touch,
- drag/drop,
- hover-only critical actions,
- hidden destructive actions,
- a guarantee of native long-press yet.

Hover feedback is an enhancement. It must not be required for critical actions.
Drag and reorder patterns may be added later, but they need keyboard and touch
fallbacks before they become part of the portable contract.

## Wraith And Appliance Guidance

Wraith-shaped and hardware-oriented Otoe surfaces should bias toward controls
that can be used while standing at a panel, operating with gloves, or running
through a keyboard-only smoke test.

- Use minimum touch targets around 44px or 48px for buttons and rows that act
  like buttons.
- Keep focus visible.
- Keep primary actions visible and directly operable.
- Place secondary actions in `...`, `More`, or future context actions.
- Put dangerous actions behind confirmation.
- Do not make critical controls hover-only.
- Maintain a required keyboard path for activation, navigation, dismissal, text
  entry, and safety confirmation.
