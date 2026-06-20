# Native Text Roadmap

Status: planning only
Last reviewed: 2026-06-16

This document evaluates native text paths for Otoe before choosing a larger Skia
or Pango/Cairo direction. It does not add dependencies and does not propose a
core implementation change yet.

## Recommendation

The next text spike should stay on the existing optional
`PillowNativeRendererBackend` path, but require an explicit bundled monospaced
font for deterministic screenshots and offline bundles. Keep marker text as the
default no-dependency baseline.

Defer Pango/Cairo until Otoe needs real paragraph layout, font fallback, and
complex text shaping on a controlled Linux appliance image. Defer Skia text
until there is a Skia raster/display-list backend to test against. Avoid SDL_ttf
as an Otoe text abstraction for now; it is useful inside an SDL host, but it
does not solve Otoe's renderer-neutral text boundary.

## Current Otoe State

- `src/otoe/_native_text.py` provides deterministic marker metrics only:
  width is derived from character count and font size, and height is derived from
  font size. It is stable for tests, but it is not real glyph rendering.
- `src/otoe/_native_pillow.py` already provides
  `PillowNativeRendererBackend(font_path=None)`. It can load Pillow's default
  font or a caller-provided TrueType/OpenType font path and uses Pillow font
  bounding boxes for measurement.
- `src/otoe/_native_paint.py` already routes text measurement into paint-time
  ellipsis logic. The current native paint path supports clipping and
  single-line ellipsis, not general wrapping.
- `docs/native-status.md` keeps marker text as the deterministic default and
  treats Pillow text as optional.
- `ADR-019-native-pillow-text-backend.md` accepted Pillow/FreeType as the first
  optional readable text backend and explicitly deferred Pango/PangoCairo and
  Skia.

## Priority Order

1. Readable screenshots for appliance UI reviews.
2. Deterministic offline bundles, including a recorded font file and hash.
3. A monospaced font path for operator consoles and log-heavy panels.
4. Predictable truncation first, then wrapping once layout v1 needs it.
5. ARM64 and Raspberry Pi installability without relying on network access at
   first run.

## Comparison Matrix

| Option | Package / binding | License and maintenance | Linux x86_64 / ARM64 | Text rendering story | Bundle risk | Expected Otoe integration | Recommendation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Current marker text | Otoe internal marker metrics and paint markers | Otoe project license; maintained with core | No external install risk on any CPU | Deterministic boxes, but no readable glyphs | Lowest | Default `NativeTextMeasurer` and marker paint path | Keep as baseline only |
| Pillow default font | `PillowNativeRendererBackend` using `ImageFont.load_default()` | Pillow is mature, MIT-CMU | Strong PyPI wheel story, including Linux x86_64 and aarch64 | Readable local smoke text; limited font coverage | Medium: output depends on Pillow version and bundled default font behavior | Optional `--native-text pillow` without `--font` | Allow for quick local smoke, not release artifacts |
| Pillow explicit font | `PillowNativeRendererBackend(font_path=...)` using `ImageFont.truetype()` | Pillow mature; chosen font has its own license | Strong PyPI wheel story; best current ARM64/Raspberry Pi fit | Readable glyphs with deterministic metrics for a pinned font; no broad fallback story | Low if bundle records font path, size, and hash | Optional Pillow backend plus profile/bundle font policy | Immediate spike |
| Pango/Cairo | PyGObject/PangoCairo, or `pangocffi` plus `pangocairocffi`/Cairo | Pango is mature LGPL; Python binding path is mixed | Viable on controlled Linux images; pip-only install is risky because PyGObject and pycairo require native libraries/headers | Best candidate for shaping, fallback, paragraph layout, wrapping, and ellipsis | High for offline bundles unless the appliance image owns the native stack | Future `TextEngine`/measurer and renderer spike, likely Linux-only first | Defer |
| Skia text | `skia-python` | BSD; active, but PyPI classifier is beta | PyPI supports Linux x86_64 and aarch64, but Linux hosts need fontconfig/OpenGL/EGL libraries | Good fit if Otoe chooses Skia raster; basic text APIs exist, but shaping/wrapping/fallback need proof | Medium to high due to heavier wheels and native library expectations | Future Skia renderer/display-list backend, not a standalone text choice | Defer |
| SDL text options | SDL_ttf through SDL3 bindings such as PySDL3 | SDL_ttf is zlib; PySDL3 is MIT and beta | PySDL3 advertises Linux AMD64/ARM64 but downloads required binaries on first run by default | SDL_ttf wraps FreeType and HarfBuzz for SDL applications; useful for host labels, not renderer-neutral Otoe text | High for deterministic offline bundles unless vendored carefully | SDL host/debug overlay only | Avoid for Otoe text |

## Detailed Notes

### Marker Text

Marker text is the right default for core tests and no-dependency native
rendering. Its value is determinism: it does not care about fonts, fontconfig,
FreeType, host DPI, or package availability. It should remain the fallback when
optional text dependencies are absent.

It is not enough for appliance UI review because screenshots do not show
operator-facing strings. Marker text also cannot validate console readability,
ellipsis quality, line-height tuning, or theme contrast.

### Pillow

Pillow is already integrated as an optional backend. It gives Otoe real PNG text
without forcing a native GUI stack or a full Skia decision. Pillow's `ImageFont`
API supports TrueType/OpenType loading through FreeType and exposes bounding-box
measurement, which matches the current Otoe paint-time ellipsis hook.

The default font path is acceptable for local smoke tests, but not for
deterministic appliance screenshots. It can change with Pillow and has limited
coverage. A pinned explicit font is the route that matches Otoe's bundle model:
copy the font into the bundle, record the size and hash, and use the same file
for layout measurement and paint.

The immediate font target should be a monospaced face. Operator consoles benefit
from stable columns, predictable truncation, and scan-friendly numeric output.
Start with one regular mono face; defer bold/italic/fallback families until a
real need appears.

### Pango/Cairo

Pango is the strongest Linux text system candidate for the hard problems:
paragraph layout, script shaping, font fallback, wrapping, ellipsis, and
fontconfig integration. It is also the most appliance-shaped choice if the
target image is controlled, because Debian/Raspberry Pi OS can provide the
native libraries consistently.

The risk is Python packaging. PyGObject is source-distributed and requires a C
compiler/native libraries. pycairo also needs Cairo headers. The CFFI packages
are lighter Python bindings, but `pangocairocffi` is old and both Pango CFFI
projects are marked planning-stage. That makes Pango/Cairo a good deferred spike
for a controlled image, not the next default text route.

### Skia Text

Skia should be evaluated as a renderer decision, not as a text-only dependency.
`skia-python` currently advertises Linux x86_64 and aarch64 binary packages, but
its Linux notes require fontconfig and GL/EGL-related libraries. That is
reasonable for a future full native renderer, but too heavy if the only goal is
readable text in screenshots.

The text story also needs proof. Basic text measurement and drawing APIs exist,
but Otoe would still need to verify shaping, fallback, wrapping, paragraph APIs,
and offline bundle behavior on ARM64. That proof belongs after a Skia raster
spike, not before it.

### SDL Text

SDL_ttf is a practical SDL application text library: SDL_ttf 3 wraps FreeType
and HarfBuzz and is licensed under zlib. It is not the right abstraction layer
for Otoe text because it ties rendering to the SDL host and does not help a
future Pillow, Cairo, or Skia backend share measurement semantics.

PySDL3 also creates bundle concerns because it downloads SDL binaries on first
run by default. That behavior conflicts with deterministic offline appliance
bundles unless Otoe owns a separate vendoring path. Use SDL text only for SDL
host diagnostics if a host spike needs it.

## Next Spike

Do a Pillow explicit-font acceptance spike before choosing Skia or Pango/Cairo.
The spike should remain optional and skip cleanly if Pillow or the font fixture
is absent.

Acceptance criteria:

- Render a MissionExec-like screen with real text using a pinned monospaced
  font path.
- Include long command/status strings that exercise the existing ellipsis path.
- Compare marker output versus Pillow explicit-font output by artifact name, not
  by pixel-perfect assertions.
- Record the font file path, size, and SHA-256 in the bundle manifest when a
  profile supplies a font.
- Document an ARM64 wheelhouse/offline install command for the optional
  `native-text` extra, without adding a mandatory dependency.

Deferred follow-up spikes:

- Pango/Cairo Linux-only text spike under `examples/native/backend_spikes/`,
  focused on wrapping, ellipsis, fallback, and Raspberry Pi OS package names.
- Skia text spike only after a Skia raster/display-list spike exists.
- SDL host text only if the SDL window/input spike needs debug overlay text.

## Non-Goals

- No mandatory dependency change.
- No full text shaping contract yet.
- No editable text, caret, IME, accessibility, or bidirectional text policy yet.
- No commitment to Skia, Pango/Cairo, or SDL as the final native renderer.

## Sources Checked

Local:

- `src/otoe/_native_text.py`
- `src/otoe/_native_pillow.py`
- `src/otoe/_native_paint.py`
- `docs/native-status.md`
- `ADR-019-native-pillow-text-backend.md`

External, checked on 2026-06-16:

- Pillow PyPI: https://pypi.org/project/Pillow/
- Pillow ImageFont docs: https://pillow.readthedocs.io/en/stable/reference/ImageFont.html
- skia-python PyPI: https://pypi.org/project/skia-python/
- pycairo PyPI: https://pypi.org/project/pycairo/
- PyGObject PyPI: https://pypi.org/project/PyGObject/
- pangocffi PyPI: https://pypi.org/project/pangocffi/
- pangocairocffi PyPI: https://pypi.org/project/pangocairocffi/
- Pango API docs: https://docs.gtk.org/Pango/
- PySDL3 PyPI: https://pypi.org/project/PySDL3/
- SDL_ttf repository: https://github.com/libsdl-org/SDL_ttf
