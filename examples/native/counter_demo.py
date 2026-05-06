from __future__ import annotations

from pathlib import Path

from otoe import (
    Button,
    HStack,
    Text,
    VStack,
    computed,
    css,
    dispatch_native_click,
    layout_native,
    mount,
    render_native_png,
    signal,
)


COUNTER_STYLES = css(
    """
    .surface {
      padding: 16;
      gap: 10;
      width: 280;
      background: surface;
      border-color: border;
      border-width: 1;
      border-radius: 10;
    }
    .title {
      color: ink;
      font-size: 20;
      font-weight: 800;
    }
    .status {
      color: muted;
      font-size: 16;
    }
    .actions {
      gap: 8;
    }
    .button {
      width: 96;
      background: accent;
      border-color: accentDark;
      border-width: 1;
      border-radius: 8;
      color: white;
    }
    .secondary {
      background: secondary;
      border-color: secondaryBorder;
      color: ink;
    }
    """,
    tokens={
        "accent": "#2563eb",
        "accentDark": "#1d4ed8",
        "border": "#d0d7de",
        "ink": "#111827",
        "muted": "#4b5563",
        "secondary": "#eef2ff",
        "secondaryBorder": "#c7d2fe",
        "surface": "#f8fafc",
        "white": "#ffffff",
    },
)


class NativeCounterDemo:
    def __init__(self, initial: int = 0) -> None:
        self.count = signal(initial)
        self.mounted = mount(self._view())

    def layout(self):
        return layout_native(self.mounted, stylesheet=COUNTER_STYLES)

    def render(self, path: str | Path):
        return render_native_png(self.layout(), path)

    def click_decrement(self):
        layout = self.layout()
        button = layout.by_path((2, 0))
        return dispatch_native_click(self.mounted, layout, button.x + 4, button.y + 4)

    def click_increment(self):
        layout = self.layout()
        button = layout.by_path((2, 1))
        return dispatch_native_click(self.mounted, layout, button.x + 4, button.y + 4)

    def _view(self):
        return VStack(
            Text("Native Counter", className="title"),
            Text(computed(lambda: f"Count: {self.count.value}"), className="status"),
            HStack(
                Button("Decrement", className="button secondary", onClick=self._decrement),
                Button("Increment", className="button", onClick=self._increment),
                className="actions",
            ),
            className="surface",
        )

    def _decrement(self) -> None:
        self.count.set(self.count.value - 1)

    def _increment(self) -> None:
        self.count.set(self.count.value + 1)


def render_demo_frames(directory: str | Path) -> tuple[Path, Path]:
    output_dir = Path(directory)
    output_dir.mkdir(parents=True, exist_ok=True)
    before = output_dir / "native_counter_before.png"
    after = output_dir / "native_counter_after.png"

    demo = NativeCounterDemo()
    demo.render(before)
    demo.click_increment()
    demo.render(after)
    return before, after


def main() -> None:
    before, after = render_demo_frames(Path("preview") / "native")
    print(f"Wrote {before}")
    print(f"Wrote {after}")


if __name__ == "__main__":
    main()
