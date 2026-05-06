from __future__ import annotations

from pathlib import Path
from typing import Any

from otoe import (
    Button,
    For,
    HStack,
    Input,
    NativeSurface,
    Panel,
    ShortcutScope,
    Show,
    Text,
    VStack,
    computed,
    css,
    signal,
)


TASKS = (
    {
        "id": "runtime",
        "title": "Runtime bridge",
        "owner": "Core",
        "status": "Ready",
    },
    {
        "id": "input",
        "title": "Input polish",
        "owner": "Native",
        "status": "Active",
    },
    {
        "id": "docs",
        "title": "Docs pass",
        "owner": "DX",
        "status": "Queued",
    },
)


TASK_BOARD_STYLES = css(
    """
    .surface {
      width: 420;
      padding: 16;
      gap: 12;
      background: surface;
      border-color: border;
      border-width: 1;
      border-radius: 12;
    }
    .ui-shortcut-scope {
      padding: 0;
    }
    .header {
      gap: 8;
    }
    .title {
      color: ink;
      font-size: 20;
    }
    .muted {
      color: muted;
      font-size: 14;
    }
    .toolbar {
      gap: 8;
    }
    .search {
      width: 210;
      background: white;
      border-color: border;
      border-width: 1;
      border-radius: 8;
    }
    .button {
      width: 84;
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
    .stats {
      gap: 8;
    }
    .pill {
      padding: 6;
      background: secondary;
      border-color: secondaryBorder;
      border-width: 1;
      border-radius: 999;
      color: ink;
      font-size: 13;
    }
    .list {
      gap: 8;
    }
    .row {
      gap: 8;
      padding: 8;
      background: white;
      border-color: border;
      border-width: 1;
      border-radius: 10;
    }
    .cell-title {
      width: 140;
      color: ink;
      font-size: 15;
    }
    .cell-meta {
      width: 70;
      color: muted;
      font-size: 13;
    }
    .modal {
      padding: 12;
      gap: 8;
      background: modal;
      border-color: accent;
      border-width: 1;
      border-radius: 10;
    }
    """,
    tokens={
        "accent": "#2563eb",
        "accentDark": "#1d4ed8",
        "border": "#d0d7de",
        "ink": "#111827",
        "modal": "#eff6ff",
        "muted": "#4b5563",
        "secondary": "#eef2ff",
        "secondaryBorder": "#c7d2fe",
        "surface": "#f8fafc",
        "white": "#ffffff",
    },
)


class NativeTaskBoardDemo:
    def __init__(self) -> None:
        self.query = signal("")
        self.selected_task_id = signal(None)
        self.shortcut_count = signal(0)
        self.visible_tasks = computed(self._visible_tasks)
        self.selected_task = computed(self._selected_task)
        self.surface = NativeSurface(self._view(), stylesheet=TASK_BOARD_STYLES)

    def render(self, path: str | Path):
        return self.surface.render_png(path)

    def type_search(self, value: str):
        return self.surface.input_text(value, path=self._first_box("Input").path)

    def click_text(self, text: str):
        box = self._box_with_text(text)
        return self.surface.click(box.x + 2, box.y + 2)

    def key_down(self, key: str, **modifiers: Any):
        return self.surface.key_down(key, **modifiers)

    def visible_titles(self) -> list[str]:
        return [task["title"] for task in self.visible_tasks.value]

    def _visible_tasks(self) -> list[dict[str, str]]:
        query = self.query.value.strip().lower()
        if not query:
            return list(TASKS)
        return [
            task
            for task in TASKS
            if query in " ".join(task.values()).lower()
        ]

    def _selected_task(self) -> dict[str, str] | None:
        selected_id = self.selected_task_id.value
        for task in TASKS:
            if task["id"] == selected_id:
                return task
        return None

    def _set_query(self, value: str) -> None:
        self.query.set(value)

    def _clear_query(self) -> None:
        self.query.set("")

    def _open_task(self, task_id: str) -> None:
        self.selected_task_id.set(task_id)

    def _close_modal(self) -> None:
        self.selected_task_id.set(None)

    def _shortcut(self, payload: dict[str, Any]) -> None:
        self.shortcut_count.set(self.shortcut_count.value + 1)
        if payload["key"] == "Escape":
            self._close_modal()
        if payload["key"].lower() == "k" and (payload["ctrlKey"] or payload["metaKey"]):
            self.query.set("")

    def _view(self):
        return ShortcutScope(
            VStack(
                HStack(
                    Text("Native Task Board", className="title"),
                    Text(
                        computed(lambda: f"{len(self.visible_tasks.value)} visible"),
                        className="pill",
                    ),
                    className="header",
                ),
                HStack(
                    Input(
                        value=self.query,
                        placeholder="Search tasks",
                        className="search",
                        autoFocus=True,
                        onChange=self._set_query,
                    ),
                    Button(
                        "Clear",
                        className="button secondary",
                        onClick=self._clear_query,
                    ),
                    Button(
                        "New",
                        className="button",
                        onClick=lambda: self._open_task("runtime"),
                    ),
                    className="toolbar",
                ),
                HStack(
                    Text(
                        computed(lambda: f"Shortcuts {self.shortcut_count.value}"),
                        className="muted",
                    ),
                    Text("Ctrl+K clears search", className="muted"),
                    className="stats",
                ),
                VStack(
                    For(
                        each=self.visible_tasks,
                        key=lambda task: task["id"],
                        children=self._task_row,
                        fallback=Text("No tasks match", className="muted"),
                    ),
                    className="list",
                ),
                Show(
                    Panel(
                        Text(
                            computed(lambda: self._modal_title()),
                            className="title",
                        ),
                        Text(
                            computed(lambda: self._modal_detail()),
                            className="muted",
                        ),
                        Button(
                            "Close",
                            className="button secondary",
                            onClick=self._close_modal,
                        ),
                        className="modal",
                    ),
                    when=computed(lambda: self.selected_task.value is not None),
                ),
                className="surface",
            ),
            onKeyDown=self._shortcut,
        )

    def _task_row(self, task: dict[str, str]):
        return HStack(
            Text(task["title"], className="cell-title"),
            Text(task["owner"], className="cell-meta"),
            Text(task["status"], className="cell-meta"),
            Button(
                "Inspect",
                className="button secondary",
                onClick=lambda task_id=task["id"]: self._open_task(task_id),
            ),
            className="row",
        )

    def _modal_title(self) -> str:
        task = self.selected_task.value
        return "Inspect task" if task is None else f"Inspect {task['title']}"

    def _modal_detail(self) -> str:
        task = self.selected_task.value
        if task is None:
            return ""
        return f"{task['owner']} / {task['status']}"

    def _box_with_text(self, text: str):
        self.surface.refresh()
        for box in self.surface.layout.boxes:
            if box.text == text:
                return box
        raise KeyError(f"No native box with text {text!r}.")

    def _first_box(self, name: str):
        self.surface.refresh()
        for box in self.surface.layout.boxes:
            if box.name == name:
                return box
        raise KeyError(f"No native box named {name!r}.")


def render_demo_frames(directory: str | Path) -> tuple[Path, Path, Path]:
    output_dir = Path(directory)
    output_dir.mkdir(parents=True, exist_ok=True)
    initial = output_dir / "native_task_board_initial.png"
    filtered = output_dir / "native_task_board_filtered.png"
    modal = output_dir / "native_task_board_modal.png"

    demo = NativeTaskBoardDemo()
    demo.render(initial)
    demo.type_search("input")
    demo.render(filtered)
    demo.click_text("Inspect")
    demo.render(modal)
    return initial, filtered, modal


def main() -> None:
    for frame in render_demo_frames(Path("preview") / "native"):
        print(f"Wrote {frame}")


if __name__ == "__main__":
    main()
