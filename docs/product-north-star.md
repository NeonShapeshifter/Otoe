# Product North Star

Otoe is a pre-alpha Python-first frontend runtime for local operational
interfaces: hardware control panels, kiosks, appliances, dashboards, offline
tools, and operator consoles.

The north star is simple: a Python developer building software for a machine
should be able to make a polished, testable, offline-capable interface without
making a browser the required runtime and without splitting the product across
an unrelated frontend stack.

Wraith inspired the need. Wraith should not define the product boundary. Otoe
must stand on its own as a public runtime for many appliance-shaped products.

## The Real Problem

Python is a natural language for hardware makers and appliance builders. It is
used for device adapters, local services, scripts, diagnostics, automation, and
operator workflows. The frontend options around that work are less natural:

- Python-native UI stacks can work, but often make it hard to reach a modern,
  product-quality visual standard.
- Browser stacks have excellent composition and styling, but bring a full web
  runtime, browser assumptions, and deployment weight that may not fit an
  offline appliance or kiosk.
- General desktop frameworks solve broad app problems, but often pull the
  product away from a Python-centered operational model.

Otoe exists for that gap. It should let teams build serious local interfaces
where the UI, reactive state, device-facing actions, build policy, test
evidence, and deployment artifacts are all understandable from Python.

## Not Another Generic UI Framework

Otoe is not trying to replace Qt, Flutter, Electron, React, or the browser. It
is narrower and more opinionated.

Its core audience builds interfaces for controlled environments:

- a device on a bench,
- a kiosk in a lobby,
- an appliance under a cabinet,
- an operations dashboard on a local network,
- an offline diagnostic or control tool,
- a private/reference product runtime that needs a professional operator
  surface.

That focus explains Otoe's product bets:

- component functions and reactive state in Python,
- a portable CSS-like style subset instead of full browser CSS,
- native render evidence instead of HTML-only screenshots,
- input contracts that work across touch, mouse, and keyboard,
- offline bundle artifacts that can be audited before deployment,
- backend boundaries that let future renderers prove support rather than claim
  it informally.

Generic UI frameworks optimize for maximum app shape. Otoe should optimize for
controlled product surfaces that need deterministic behavior, clear deployment,
and professional operational UI.

## Why Kivy Is Not Enough For This Goal

Kivy works, and Wraith proves that a Python-native UI can ship a real
operator-facing product. The issue is not whether Kivy can make screens. The
issue is whether it gives Otoe's target audience the fastest path to a polished,
modern, product-grade appliance interface.

For Otoe's goal, the runtime needs stronger alignment around:

- component composition that feels natural to Python app authors,
- CSS-like styling and reusable visual primitives,
- fast preview while iterating on dense UI,
- deterministic render and input tests,
- offline build outputs with manifest and dependency evidence,
- a public product story that is not tied to one application.

Kivy remains a useful point of comparison, especially because it demonstrates
the value of Python-native UI. Otoe's ambition is different: it should make
hardware and operational software feel closer to a modern product surface while
keeping the runtime Python-first and appliance-aware.

## Why A Browser Is Not The Primary Runtime

Otoe borrows from the web, but it should not require a full browser as the
runtime contract.

A browser is excellent for fast preview. It gives familiar rendering, quick
iteration, and rich developer feedback. Otoe should keep that advantage.

The primary product runtime, however, has different constraints:

- appliances may run offline or on tightly controlled networks,
- kiosks often need locked-down deployment under Cage, Weston, or similar
  shells,
- hardware interfaces need predictable input and focus behavior,
- deployment should be auditable through local artifacts,
- future native backends need a contract smaller than DOM plus full CSS,
- security and update boundaries should not inherit unnecessary browser
  surface area by default.

This does not make browsers bad. It means browser preview is a development
surface, and possibly one deploy target later, but not the definition of Otoe.
Otoe's product contract must be able to survive without a DOM.

## Python-First Frontend For Hardware Appliances

Python-first means the frontend model starts where hardware and operator code
already lives:

- component functions are Python functions,
- state is Python reactive state,
- events call Python handlers,
- device adapters, local services, and fake providers can share the same
  language boundary,
- tests can drive the mounted tree and native surface without a browser,
- builds can collect Python runtime files, dependency audits, styles, and
  renderer artifacts into an offline bundle.

For hardware appliances, this also means the UI must respect physical use:

- touch targets that work while standing at a panel,
- keyboard paths for smoke tests and field operation,
- visible focus and safe confirmation flows,
- local-first behavior when the network is absent,
- predictable startup and deployment artifacts.

Otoe should feel like frontend work for Python-operated machines, not like a
web app awkwardly embedded beside Python.

## What Otoe Takes From The Web

Otoe should take the parts of the web that make interface work productive:

- declarative composition,
- reusable components,
- class-based styling,
- a CSS-like authoring model,
- fast static and live preview,
- inspectable build artifacts,
- familiar layout vocabulary,
- clear separation between app logic, style, assets, and runtime output.

It should not copy the web wholesale. Full CSS parity, DOM APIs, browser
layout semantics, and browser extension points are not the current contract.
The portable subset exists because hardware and native targets need a smaller,
testable surface that can be compiled into artifacts and replayed outside a
browser.

## Why These Technical Pieces Exist

### Native Render

Native render exists to prove that Otoe is not only an HTML preview library. The
current native path is still experimental and headless, but it gives the project
deterministic layout, paint, PNG output, hit testing, focus, keyboard input,
text input, and scroll evidence.

That evidence matters because future native backends should be accepted by
contract: layout behavior, paint output, input behavior, and artifact replay
must be demonstrable before Otoe can claim production native support.

### CSS Subset

The CSS subset exists because app authors need familiar styling, but appliance
targets need portability. Otoe currently supports selected portable properties,
simple values, class selectors, style IR, and low-level styleOps artifacts.

This is not full browser CSS. It is a product boundary: styles that enter the
portable contract should be understandable by native render, offline planning,
bundle validation, and backend-candidate evidence.

### Offline Bundles

Offline bundles exist because appliance software must be deployable and
reviewable without assuming a live web build pipeline on the target.

An Otoe bundle should make the runtime shape explicit: app files, framework
files, assets, dependency audit metadata, compiled style artifacts, RenderTree
artifacts, hashes, manifest data, and a generated runner that can verify and
load the bundle.

This is not a sandbox. It is an audit and deployment contract.

### Input Core

The input core exists because hardware and kiosk interfaces cannot rely on only
one interaction mode. A useful appliance surface must work across touch, mouse,
keyboard, focus movement, activation, text entry, scroll, dismissal, shortcuts,
and safe confirmation.

Input behavior must be testable in preview and native paths. Hidden hover-only
actions, untestable gesture dependencies, and unclear focus behavior make an
operator UI less reliable.

### Build Artifacts

Build artifacts exist so product claims can be checked. `otoe-styles.json`,
`styleOps`, `otoe-render-tree.json`, dependency reports, manifests, backend
coverage, and runner verification turn renderer and deployment assumptions into
files that CI, humans, and future backend candidates can inspect.

Otoe should earn trust through artifacts, not through vague compatibility
claims.

## Ideal Users

### Hardware Makers

People building Python-controlled devices, lab tools, embedded panels,
diagnostics consoles, manufacturing fixtures, or field equipment. They need
local UI that is direct, touchable, testable, and shippable.

### Appliance Builders

Teams packaging a Python runtime into a controlled product. They care about
offline operation, repeatable deployment, predictable startup, update
boundaries, and visual polish.

### Python Developers

Developers who can build the domain logic, device adapters, and local services
in Python, and want the frontend to share that mental model instead of forcing a
separate JavaScript product stack.

### Operators And Internal Tools Teams

Teams building dashboards, control rooms, workflow tools, local admin consoles,
and diagnostic panels where clarity, density, safety, and repeatable behavior
matter more than marketing-page flexibility.

### Kiosk And Control Panel Builders

Builders who need locked-down interfaces with large controls, predictable
input, offline assets, and deployment artifacts that can run in constrained
Linux environments.

## Anti-Goals

Otoe should be explicit about what it is not promising yet:

- no production desktop renderer promise today,
- no full CSS browser parity today,
- no DOM clone or browser API clone,
- no stable public API while the project is pre-alpha,
- no claim that every `otoe.ui` component has complete native parity,
- no claim that offline bundles are a security sandbox,
- no generic replacement promise for every desktop, mobile, or web app.

These anti-goals are not a lack of ambition. They keep the product honest while
the runtime earns reliability.

## What Otoe Must Prove Before Public Trust

Before Otoe can be treated as a reliable public product surface, it must
demonstrate more than attractive examples.

It should prove:

- a polished non-Wraith hardware control panel can be authored, previewed,
  rendered natively, bundled, and validated;
- native text, layout, paint, and input behavior are credible enough for
  appliance UI evidence;
- the portable CSS subset is documented, enforced, and useful for real
  product surfaces;
- offline builds are repeatable from clean environments and fail clearly when
  artifacts drift;
- input behavior works across touch, mouse, keyboard, focus, scroll, and safe
  confirmation paths;
- API tiers are documented and experimental surfaces are clearly labeled;
- security and trust boundaries are documented without implying sandboxing;
- backend candidates can be evaluated through artifacts and acceptance gates;
- examples and docs set expectations for pre-alpha users instead of implying a
  stable framework.

The public message should stay ambitious but precise:

Otoe is not yet a stable framework. It is a focused pre-alpha runtime trying to
make Python-first appliance frontends feel professional, testable, and
deployable without making the browser the mandatory center of the product.
