from __future__ import annotations

import sys
from pathlib import Path
from typing import Sequence

from otoe import NativeWindowDriver, run_native

from .task_board_demo import NativeTaskBoardDemo


class NativeWindowDemo:
    def __init__(self) -> None:
        self.board = NativeTaskBoardDemo()
        self.driver = NativeWindowDriver(self.board.surface)

    def render(self, path: str | Path):
        return self.driver.render_png(path)

    def type_search(self, value: str):
        return self.driver.input_text(value)

    def clear_with_shortcut(self):
        return self.driver.key_down("k", ctrl=True)

    def scroll_list(self, delta_y: int):
        box = self._first_box("ScrollView")
        return self.driver.wheel(box.x + 2, box.y + 2, delta_y)

    def open_first_visible_task(self):
        box = self._box_with_text("Inspect")
        return self.driver.click(box.x + 2, box.y + 2)

    def visible_titles(self) -> list[str]:
        return self.board.visible_titles()

    def _box_with_text(self, text: str):
        for box in self.driver.surface.layout.boxes:
            if box.text == text:
                return box
        raise KeyError(f"No native window box with text {text!r}.")

    def _first_box(self, name: str):
        for box in self.driver.surface.layout.boxes:
            if box.name == name:
                return box
        raise KeyError(f"No native window box named {name!r}.")


def render_demo_frames(directory: str | Path) -> tuple[Path, Path, Path, Path]:
    output_dir = Path(directory)
    output_dir.mkdir(parents=True, exist_ok=True)
    initial = output_dir / "native_window_initial.png"
    filtered = output_dir / "native_window_filtered.png"
    modal = output_dir / "native_window_modal.png"
    shortcut = output_dir / "native_window_shortcut.png"

    demo = NativeWindowDemo()
    demo.render(initial)
    demo.type_search("input")
    demo.render(filtered)
    demo.open_first_visible_task()
    demo.render(modal)
    demo.clear_with_shortcut()
    demo.render(shortcut)
    return initial, filtered, modal, shortcut


def run_window() -> None:
    demo = NativeWindowDemo()
    run_native(demo.driver, title="Otoe Native Window Demo")


def main(argv: Sequence[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    if args == ["--window"]:
        run_window()
        return
    if args:
        raise SystemExit("Usage: python -m examples.native.window_demo [--window]")

    for frame in render_demo_frames(Path("preview") / "native"):
        print(f"Wrote {frame}")


if __name__ == "__main__":
    main()
