# Native Backend Stack Matrix

Status: experimental research, not onboarding guidance
Last checked: 2026-06-16.

This document evaluates realistic Python-facing options for the future Otoe
native stack described in
[`ADR-021`](../ADR-021-native-yoga-skia-sdl3-roadmap.md) and the current
native limits in [`native-status.md`](native-status.md).

No option listed here is a current Otoe dependency. The default Otoe runtime
should stay dependency-light. Native engines should enter through optional
backend packages and Otoe's existing layout, paint/raster, text, and host
boundaries.

## Executive Recommendation

Immediate spike:

- Build the next technical step as the display-list boundary first, as ADR-021
  already says.
- After that, spike `skia-python` as an optional CPU raster backend for
  display-list-to-PNG and display-list-to-pixels. Current wheels exist for
  Linux `x86_64` and `aarch64`, but the target image must provide fontconfig,
  OpenGL/EGL, and Mesa/libglvnd libraries.
- In parallel or immediately after, spike `PySDL3` only as a host proof:
  open a window, present a CPU buffer, and report input. Do not rely on
  PySDL3's first-run binary downloader for Otoe offline bundles.
- Use a small Pango/Cairo text-measurement probe on Linux when Yoga/text sizing
  becomes the blocker. Pango is the credible long-term Linux text shaping
  story, but packaging it through pip-only wheels is weak.

Deferred:

- A real Yoga layout backend. The official Yoga project is active, but there
  is no credible maintained Python wheel path today. Otoe likely needs its own
  narrow binding or native extension if Yoga remains the selected layout
  engine.
- Taffy as an alternate layout engine. It is active and attractive in Rust, but
  there is no usable Python binding. It implies owning a PyO3/maturin wheel
  pipeline.
- Production SDL3 packaging. SDL3/Wayland/Cage is viable architecturally, but
  the packaging story must be made explicit with system packages, vendored
  libraries, or self-built wheels before it can be an appliance claim.
- Full Pango/PangoCairo integration. It should be the text shaping direction,
  not a first renderer dependency.

Avoid for now:

- PyPI `yoga`: it is an image optimization package, not Facebook/React Yoga
  layout.
- PyPI `taffy`: it is a comparative genomics package, not the Taffy layout
  engine.
- `pygame-ce` as the Otoe native host. It is SDL2-based and game-framework
  shaped; it owns too much of the event/rendering model for Otoe's backend
  boundary.
- `PySDL2`/`pysdl2-dll` for the ADR-021 path. Useful as SDL ecosystem context
  and a possible emergency fallback, but it does not validate SDL3.
- Cairo toy text as the serious text plan. It is fine for tiny smoke output,
  but not for appliance-quality shaping, wrapping, or fallback.

## Deployment Assumptions

- Linux `aarch64` does not automatically mean Raspberry Pi support. It means a
  64-bit ARM Linux userspace with compatible glibc and system libraries.
  32-bit Raspberry Pi OS is out of scope for this stack unless Otoe owns custom
  builds.
- A realistic Pi target should start with 64-bit Raspberry Pi OS Bookworm or a
  similar 64-bit image, Wayland enabled, and a known package set for SDL3,
  fontconfig, Mesa/EGL, Cairo, Pango, HarfBuzz, and FreeType.
- Cage is a good deployment shape for a single fullscreen app. It is not an
  Otoe dependency; it is the compositor/session below the SDL3 app.
- Offline bundle viability means a prebuilt wheelhouse plus declared OS image
  packages or copied shared libraries. Any first-run downloader is a release
  blocker for Otoe appliances.

## Layout Options

| Option | Package or binding | License | Maintenance | Wheels available | Linux x86_64 | Linux ARM64 | Raspberry Pi viability | Wayland/Cage viability | Text rendering story | Packaging/offline risk | Expected Otoe integration | Recommendation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Official Yoga | No credible Python package. Upstream C/C++ library at `react/yoga` | MIT | Active upstream; repo pushed 2026-06-09 | No Python wheels | Viable only if Otoe builds/bundles a binding | Viable only if Otoe builds/bundles a binding | Plausible on 64-bit Pi, but Otoe would own build and ABI testing | Indirect; layout engine is display-server agnostic | None. Yoga needs measure callbacks from an Otoe text measurement backend | High. Requires self-owned binding, CI, wheels, and ABI policy | `LayoutBackend.compute(layout_tree, constraints) -> LayoutResult` | Deferred. Keep as ADR target, but do not start here |
| PyPI `yoga` | `yoga` | BSD-3-Clause | Active, but unrelated to layout | Many wheels, Linux x86_64 only for latest release | Installable, but wrong package | No Linux ARM64 wheel in latest release | Not relevant | Not relevant | Not relevant | High because package name is misleading | None | Avoid |
| Taffy upstream | Rust crate `taffy`, not a Python binding | MIT | Active; repo pushed 2026-06-15, crate file showed `0.11.0` | No Python wheels | Viable only via custom PyO3/cffi binding | Viable only via custom PyO3/cffi binding | Plausible on 64-bit Pi if Otoe owns Rust wheel builds | Indirect; layout engine is display-server agnostic | None. Needs text measure callbacks | High. Adds Rust toolchain and wheel ownership | Alternate `LayoutBackend` behind the same contract as Yoga | Deferred as alternate research, not the ADR-021 first path |
| PyPI `taffy` | `taffy` | MIT | Active enough, but unrelated to UI layout | Latest had only macOS ARM wheel plus sdist | Not suitable | Not suitable | Not relevant | Not relevant | Not relevant | High because package name collides with the layout engine | None | Avoid |

## Paint, Raster, And Text Options

| Option | Package or binding | License | Maintenance | Wheels available | Linux x86_64 | Linux ARM64 | Raspberry Pi viability | Wayland/Cage viability | Text rendering story | Packaging/offline risk | Expected Otoe integration | Recommendation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Skia via `skia-python` | `skia-python` | BSD-3-Clause | Active; PyPI `144.0.post2` uploaded 2026-03-19, repo pushed 2026-06-11 | CPython wheels include Linux `manylinux_2_28_x86_64` and `manylinux_2_28_aarch64` | Good for optional spike if host has required shared libs | Good on paper via aarch64 wheels | Plausible on 64-bit Pi, but must test import, CPU raster, fontconfig, EGL, and memory use | Indirect. Skia produces pixels; SDL3 presents them under Wayland/Cage | Useful basic text APIs, but full shaping/fallback should not be assumed for Otoe V0 | Medium-high. Wheelhouse is feasible, but Linux hosts still need fontconfig, OpenGL/EGL, Mesa/libglvnd libraries | `PaintBackend` for display-list-to-PNG and display-list-to-pixels; later pixels feed `HostBackend.present(frame)` | Immediate spike after display list |
| Cairo only via `pycairo` | `pycairo` | LGPL-2.1-only OR MPL-1.1 | Active; PyPI `1.29.0` uploaded 2025-11-11, repo pushed 2026-04-28 | Latest PyPI has Windows wheels and sdist; no Linux wheels | Works well from distro packages or source builds | Works well from distro packages or source builds | Good through Debian/Raspberry Pi OS packages | Indirect; produces image surfaces or can draw in memory | Cairo toy text is not enough for serious UI text | Medium-high for pip-only bundles; lower if OS image owns Cairo | Possible alternate `PaintBackend` or test renderer, but not primary ADR-021 paint path | Deferred; avoid toy text as text strategy |
| Pango/PangoCairo via `PyGObject` plus `pycairo` | `PyGObject`, `pycairo`, system Pango/Cairo GI packages | PyGObject LGPL-2.1; pycairo LGPL-2.1/MPL-1.1 | Active GNOME stack; PyPI `PyGObject 3.56.3` uploaded 2026-05-08 | PyGObject latest is sdist only; pycairo Linux is source/distro package path | Strong on Linux with distro packages | Strong on Linux ARM64 with distro packages | Strongest Pi text story if OS image owns packages | Indirect; text/image output can feed SDL3/Skia/Cairo surfaces | Best serious Linux text shaping, wrapping, font fallback, and measurement direction | High for pip-only offline bundles; acceptable for controlled appliance images with pinned OS packages | `TextMeasurementBackend`; later `TextPaintBackend` or Pango-to-glyph/display-list support | Deferred for production, but useful as an early text measurement probe |
| Cairo/Pango via CFFI packages | `cairocffi`, `pangocffi`, `pangocairocffi` | cairocffi BSD-3-Clause; Pango CFFI packages LGPL-2.1 | Mixed. `cairocffi` active; `pangocffi` released 2026-01-28; `pangocairocffi` latest PyPI release is 2022-10-07 but repo activity exists | `cairocffi` has pure Python wheel; `pangocffi` and `pangocairocffi` latest releases are sdist only | Viable with system Cairo/Pango libs | Viable with system Cairo/Pango libs | Plausible on 64-bit Pi with OS packages | Indirect | Pango is good, but these bindings explicitly say they are not fully implemented | Medium-high. Fewer GI requirements, but still relies on shared libraries and incomplete bindings | Possible narrow `TextMeasurementBackend` experiment if GI is too heavy | Deferred; do not bet production text on it yet |
| Pillow/FreeType current path | Existing optional Otoe native text path via Pillow | HPND/PIL-style for Pillow | Already integrated in Otoe as optional readable PNG text path | Pillow has broad wheels including Linux ARM64 | Works today for headless PNG | Works today where Pillow wheels are available | Practical for screenshots and basic offline evidence | Not a windowing solution | Readable simple text, not full shaping/fallback | Low-medium. Otoe already supports explicit bundled font path | Existing `PillowNativeRendererBackend` for headless PNG text | Keep as baseline, not final native appliance text |

## Host, Windowing, And Input Options

| Option | Package or binding | License | Maintenance | Wheels available | Linux x86_64 | Linux ARM64 | Raspberry Pi viability | Wayland/Cage viability | Text rendering story | Packaging/offline risk | Expected Otoe integration | Recommendation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SDL3 C library | `libsdl-org/SDL`, used through a binding or native extension | zlib | Active; repo pushed 2026-06-16 | Not a Python wheel by itself | Strong if distro or vendored library is present | Strong if distro or vendored library is present | Plausible on 64-bit Pi with SDL3 built with Wayland/input support | Good. SDL3 favors Wayland by default on Linux and documents Wayland behavior; Cage runs one maximized app | None. SDL_ttf exists, but Otoe should keep text separate | Medium-high. Need system package, copied `.so`, or self-built wheel policy | `HostBackend`: window, input events, frame pacing, buffer/texture presentation | Deferred for production, but this is the target host layer |
| SDL3 via `PySDL3` | `PySDL3` | MIT | Active but beta; PyPI `0.9.11b1` uploaded 2026-05-06, repo pushed 2026-05-07 | Pure `py3-none-any` wheel; SDL3 binaries are not normal platform wheels | Viable for spike | Viable for spike per docs | Plausible on 64-bit Pi only if binaries are provided or system SDL3 is found | Good if the loaded SDL3 binary has Wayland support and event loop presents an initial buffer | None for Otoe; do not use SDL_ttf as the main text plan | High by default because PySDL3 can download binaries on first run. Must disable downloads and use `SDL_BINARY_PATH` or system libraries for offline bundles | First `HostBackend` proof: open window, present CPU frame, map pointer/key/text events | Immediate host spike, with offline-safe binary policy from day one |
| SDL2 via `PySDL2` plus `pysdl2-dll` | `PySDL2`, optional `pysdl2-dll` | PySDL2 Public Domain/zlib; `pysdl2-dll` MPL-2.0 | Active; PySDL2 PyPI `0.9.17` uploaded 2024-12-30, `pysdl2-dll 2.32.10` uploaded 2026-05-26 | PySDL2 pure wheel; `pysdl2-dll` has Linux `x86_64` and `aarch64` wheels | Good | Good via `pysdl2-dll` aarch64 wheels | Plausible on 64-bit Pi | Possible if bundled SDL2 has Wayland support, but this does not prove SDL3 | None for Otoe | Lower than PySDL3 for bundled binaries, but wrong major SDL version | Emergency host fallback or comparative spike only | Avoid for ADR-021 path; keep as fallback context |
| `pygame-ce` | `pygame-ce` | LGPL-2.1-or-later | Active; PyPI `2.5.7` uploaded 2026-03-02, repo pushed 2026-06-14 | Linux `x86_64` and `aarch64` wheels exist | Good | Good | Plausible on 64-bit Pi | Depends on SDL2/backend behavior; not an SDL3 validation path | Pygame font/SDL_ttf is usable for games, not Otoe's text model | Medium. Wheels are good, but framework ownership is wrong for Otoe | None as a real backend. At most a throwaway input/window smoke | Avoid for Otoe native backend |
| Cage session | `cage` compositor, not a Python package | MIT | Active; repo pushed 2026-06-12 | OS package/source build, not PyPI | Good on Wayland-capable Linux | Good on ARM64 if packaged or built | Good deployment target for kiosk/appliance images | Directly relevant. Cage runs a single maximized app and can run from TTY with KMS/DRM backend | None | OS image risk, not Python risk | Deployment wrapper below `HostBackend`, for example `cage -- otoe-native ...` | Use for hardware smoke, not before SDL3 host works |

## Practical Integration Plan

1. Keep Otoe core clean: no Yoga, Skia, SDL3, Pango, Cairo, or PyGObject imports
   in default paths.
2. Land or harden a serializable display-list IR before native engines.
3. Add a `skia-python` optional backend package experiment that renders the
   display list to PNG/pixels with an explicit font path and clear
   unavailable errors.
4. Add a `PySDL3` host experiment that can present an existing pixel buffer and
   translate SDL events into Otoe native input events. Disable or avoid
   first-run binary downloads in the experiment.
5. Run the first hardware smoke on Linux x86_64 before Raspberry Pi. Then run a
   64-bit Pi smoke under Wayland/Cage with the same app and documented OS
   packages.
6. Only after paint and host are proven, decide whether Yoga gets a self-owned
   binding or whether Taffy deserves a Rust binding spike.
7. Treat Pango/PangoCairo as the serious text measurement and shaping track.
   Keep Pillow as the current screenshot baseline until Pango or Skia text
   proves better inside Otoe's backend boundary.

## Offline Bundle Notes

- `skia-python` is now more realistic than older ADR risk language implied,
  because Linux `aarch64` wheels exist. The remaining risk is native shared
  libraries and target-image compatibility, not absence of wheels.
- `PySDL3` is the opposite shape: the Python wheel is easy, but the default
  binary acquisition behavior is hostile to offline appliance bundles. Otoe
  must require explicit SDL3 binary discovery or bundled libraries.
- PyGObject/Pango/Cairo should be handled as appliance OS dependencies first,
  not as pure pip dependencies. A Pi image can be repeatable without every
  native library being a Python wheel.
- For every native option, the bundle manifest should record the backend
  package, imported Python packages, copied fonts/assets, and a target-image
  dependency note for required `.so` libraries.

## Sources Checked

- Otoe local docs: [`ADR-021`](../ADR-021-native-yoga-skia-sdl3-roadmap.md),
  [`native-status.md`](native-status.md), [`build-offline.md`](build-offline.md),
  and [`layout-v1-plan.md`](layout-v1-plan.md).
- Yoga: <https://github.com/facebook/yoga> and
  <https://github.com/facebook/yoga/blob/main/LICENSE>.
- Taffy: <https://github.com/DioxusLabs/taffy> and its `Cargo.toml`.
- Skia: <https://pypi.org/project/skia-python/>,
  <https://github.com/skia-python/skia-python>, and
  <https://kyamagu.github.io/skia-python/install.html>.
- Cairo/Pango: <https://pypi.org/project/pycairo/>,
  <https://github.com/pygobject/pycairo>,
  <https://pypi.org/project/PyGObject/>,
  <https://gitlab.gnome.org/GNOME/pygobject>,
  <https://pypi.org/project/cairocffi/>,
  <https://github.com/Kozea/cairocffi>,
  <https://pypi.org/project/pangocffi/>,
  <https://github.com/leifgehrmann/pangocffi>,
  <https://pypi.org/project/pangocairocffi/>, and
  <https://github.com/leifgehrmann/pangocairocffi>.
- SDL3 and Python bindings: <https://github.com/libsdl-org/SDL>,
  <https://github.com/libsdl-org/SDL/blob/main/docs/README-linux.md>,
  <https://github.com/libsdl-org/SDL/blob/main/docs/README-wayland.md>,
  <https://pypi.org/project/PySDL3/>,
  <https://pysdl3.readthedocs.io/en/latest/install.html>, and
  <https://github.com/Aermoss/PySDL3>.
- SDL2 and pygame context: <https://pypi.org/project/PySDL2/>,
  <https://github.com/py-sdl/py-sdl2>,
  <https://pypi.org/project/pysdl2-dll/>,
  <https://pypi.org/project/pygame-ce/>, and
  <https://github.com/pygame-community/pygame-ce>.
- Cage: <https://github.com/cage-kiosk/cage>.
