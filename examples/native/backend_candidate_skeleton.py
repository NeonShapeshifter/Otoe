from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from typing import Any

from otoe import (
    Button,
    HStack,
    Input,
    NativeWindowDriver,
    NativeWindowEvent,
    ScrollView,
    ShortcutScope,
    Text,
    VStack,
    component,
    computed,
    css,
    run_native,
    signal,
)

from .window_demo import NativeWindowDemo


TASK_BOARD_TITLES = ("Runtime bridge", "Input polish", "Docs pass")


@dataclass(frozen=True)
class MinimalBackendCandidateReplay:
    title: str
    initial_frame: int
    final_frame: int
    initial_focus: tuple[str, str | None] | None
    final_focus: tuple[str, str | None] | None
    echo_visible: bool
    clicked_visible: bool
    shortcut_visible: bool
    scrolled: bool

    @property
    def passed(self) -> bool:
        return (
            self.final_frame > self.initial_frame
            and self.initial_focus == ("Input", "seed")
            and self.echo_visible
            and self.clicked_visible
            and self.shortcut_visible
            and self.scrolled
        )


@dataclass(frozen=True)
class TaskBoardBackendCandidateReplay:
    title: str
    initial_frame: int
    final_frame: int
    filtered_titles: tuple[str, ...]
    modal_visible_after_click: bool
    modal_closed_after_escape: bool
    shortcut_text_after_escape: str | None
    reset_titles: tuple[str, ...]
    scrolled: bool
    final_focus: tuple[str, str | None] | None

    @property
    def passed(self) -> bool:
        return (
            self.final_frame > self.initial_frame
            and self.filtered_titles == ("Input polish",)
            and self.modal_visible_after_click
            and self.modal_closed_after_escape
            and self.shortcut_text_after_escape == "Shortcuts 1"
            and self.reset_titles == TASK_BOARD_TITLES
            and self.scrolled
            and self.final_focus is not None
        )


@dataclass(frozen=True)
class BackendCandidateAcceptanceReport:
    minimal: MinimalBackendCandidateReplay
    task_board: TaskBoardBackendCandidateReplay

    @property
    def passed(self) -> bool:
        return self.minimal.passed and self.task_board.passed


@dataclass(frozen=True)
class HeadlessCandidateFrameSummary:
    label: str
    frame: int
    size: tuple[int, int]
    root_name: str
    focused: tuple[str, str | None] | None
    layout_boxes: int
    paint_commands: int
    visible_text: tuple[str, ...]
    paint_kinds: tuple[str, ...]


@dataclass(frozen=True)
class HeadlessCandidateRunReport:
    backend: str
    title: str
    before: HeadlessCandidateFrameSummary
    after: HeadlessCandidateFrameSummary
    replay: object

    @property
    def passed(self) -> bool:
        return (
            bool(getattr(self.replay, "passed", False))
            and self.after.frame > self.before.frame
            and self.after.layout_boxes > 0
            and self.after.paint_commands > 0
        )


@dataclass(frozen=True)
class HeadlessCandidateAcceptanceReport:
    minimal: HeadlessCandidateRunReport
    task_board: HeadlessCandidateRunReport

    @property
    def passed(self) -> bool:
        return self.minimal.passed and self.task_board.passed


class RecordingBackendCandidate:
    """Small adapter skeleton for backend-candidate acceptance replays."""

    name = "recording-candidate"

    def __init__(
        self,
        replay: Callable[..., object],
    ) -> None:
        self._replay = replay
        self.replays: list[object] = []

    def run(self, driver: NativeWindowDriver, *, title: str = "Otoe") -> None:
        self.replays.append(self._replay(driver, title=title))


class HeadlessCandidateBackend:
    """No-window candidate adapter that records replay/layout/paint summaries."""

    name = "headless-candidate"

    def __init__(
        self,
        replay: Callable[..., object],
        *,
        name: str | None = None,
    ) -> None:
        self.name = name or self.name
        self._replay = replay
        self.reports: list[HeadlessCandidateRunReport] = []

    def run(self, driver: NativeWindowDriver, *, title: str = "Otoe") -> None:
        before = summarize_headless_candidate_frame(driver, label="before")
        replay = self._replay(driver, title=title)
        after = summarize_headless_candidate_frame(driver, label="after")
        self.reports.append(
            HeadlessCandidateRunReport(
                backend=self.name,
                title=title,
                before=before,
                after=after,
                replay=replay,
            )
        )


def run_backend_candidate_acceptance() -> BackendCandidateAcceptanceReport:
    minimal_backend = RecordingBackendCandidate(replay_minimal_candidate)
    run_native(
        backend_candidate_app(),
        stylesheet=BACKEND_CANDIDATE_STYLES,
        title="Backend Candidate Minimal",
        backend=minimal_backend,
    )

    task_board_backend = RecordingBackendCandidate(replay_task_board_candidate)
    run_native(
        NativeWindowDemo().driver,
        title="Backend Candidate Task Board",
        backend=task_board_backend,
    )

    return BackendCandidateAcceptanceReport(
        minimal=_last_replay(minimal_backend, MinimalBackendCandidateReplay),
        task_board=_last_replay(task_board_backend, TaskBoardBackendCandidateReplay),
    )


def run_headless_candidate_acceptance() -> HeadlessCandidateAcceptanceReport:
    minimal_backend = HeadlessCandidateBackend(replay_minimal_candidate)
    run_native(
        backend_candidate_app(),
        stylesheet=BACKEND_CANDIDATE_STYLES,
        title="Headless Candidate Minimal",
        backend=minimal_backend,
    )

    task_board_backend = HeadlessCandidateBackend(replay_task_board_candidate)
    run_native(
        NativeWindowDemo().driver,
        title="Headless Candidate Task Board",
        backend=task_board_backend,
    )

    return HeadlessCandidateAcceptanceReport(
        minimal=_last_report(minimal_backend),
        task_board=_last_report(task_board_backend),
    )


def acceptance_report_to_dict(
    report: HeadlessCandidateAcceptanceReport,
) -> dict[str, Any]:
    payload = asdict(report)
    payload["passed"] = report.passed
    payload["minimal"]["passed"] = report.minimal.passed
    payload["task_board"]["passed"] = report.task_board.passed
    payload["minimal"]["replay"]["passed"] = bool(
        getattr(report.minimal.replay, "passed", False)
    )
    payload["task_board"]["replay"]["passed"] = bool(
        getattr(report.task_board.replay, "passed", False)
    )
    return payload


def format_acceptance_report(report: HeadlessCandidateAcceptanceReport) -> str:
    lines = [
        "backend candidate acceptance",
        f"status: {'passed' if report.passed else 'failed'}",
        _format_run_report("minimal", report.minimal),
        _format_run_report("task_board", report.task_board),
    ]
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m examples.native.backend_candidate_skeleton",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print the headless candidate acceptance report as JSON",
    )
    args = parser.parse_args(argv)
    report = run_headless_candidate_acceptance()

    if args.json:
        print(json.dumps(acceptance_report_to_dict(report), indent=2, sort_keys=True))
    else:
        print(format_acceptance_report(report))
    return 0 if report.passed else 1


def backend_candidate_app():
    query = signal("seed")
    clicked = signal("none")
    shortcuts = signal(0)
    scroll_y = signal(0)

    @component
    def CandidateApp():
        return ShortcutScope(
            VStack(
                Input(
                    value=query,
                    autoFocus=True,
                    onChange=lambda next_value: query.set(next_value),
                    className="candidate-input",
                ),
                HStack(
                    Button("One", onClick=lambda: clicked.set("one")),
                    Button("Two", onClick=lambda: clicked.set("two")),
                    className="candidate-toolbar",
                ),
                ScrollView(
                    Button("First", onClick=lambda: clicked.set("first")),
                    Button("Second", onClick=lambda: clicked.set("second")),
                    scrollY=scroll_y,
                    onScroll=lambda next_scroll_y: scroll_y.set(next_scroll_y),
                    className="candidate-list",
                ),
                Text(computed(lambda: f"Echo {query.value}")),
                Text(computed(lambda: f"Clicked {clicked.value}")),
                Text(computed(lambda: f"Shortcuts {shortcuts.value}")),
                className="candidate-shell",
            ),
            onKeyDown=lambda _payload: shortcuts.set(shortcuts.value + 1),
        )

    return CandidateApp()


BACKEND_CANDIDATE_STYLES = css(
    """
    .ui-shortcut-scope {
    }
    .candidate-shell {
      width: 220;
      padding: 8;
      gap: 6;
      background: #f8fafc;
    }
    .candidate-input {
      width: 120;
    }
    .candidate-toolbar {
      width: 200;
      height: 44;
      gap: 4;
      align-items: center;
      justify-content: space-between;
    }
    .candidate-list {
      width: 200;
      height: 44;
      padding: 4;
      gap: 4;
      background: #ffffff;
    }
    """
)


def replay_minimal_candidate(
    driver: NativeWindowDriver,
    *,
    title: str = "Otoe",
) -> MinimalBackendCandidateReplay:
    initial_frame = driver.frame
    initial_focus = focused_box_summary(driver)

    driver.dispatch(NativeWindowEvent("input_text", text="alpha"))
    echo_visible = has_layout_text(driver, "Echo alpha")

    driver.dispatch(NativeWindowEvent("key_input", key="k", text="k", ctrl=True))
    shortcut_visible = has_layout_text(driver, "Shortcuts 1")

    button = box_with_text(driver, "Two")
    driver.click(button.x + 2, button.y + 2)
    clicked_visible = has_layout_text(driver, "Clicked two")

    scroll_box = first_box(driver, "ScrollView")
    first_before = box_with_text(driver, "First")
    driver.wheel(scroll_box.x + 2, scroll_box.y + 2, 80)
    scrolled = box_with_text(driver, "First").y < first_before.y

    return MinimalBackendCandidateReplay(
        title=title,
        initial_frame=initial_frame,
        final_frame=driver.frame,
        initial_focus=initial_focus,
        final_focus=focused_box_summary(driver),
        echo_visible=echo_visible,
        clicked_visible=clicked_visible,
        shortcut_visible=shortcut_visible,
        scrolled=scrolled,
    )


def replay_task_board_candidate(
    driver: NativeWindowDriver,
    *,
    title: str = "Otoe",
) -> TaskBoardBackendCandidateReplay:
    initial_frame = driver.frame

    driver.input_text("input")
    filtered_titles = visible_task_titles(driver)

    inspect = box_with_text(driver, "Inspect")
    driver.click(inspect.x + 2, inspect.y + 2)
    modal_visible = has_layout_text(driver, "Inspect Input polish")

    driver.key_down("Escape")
    modal_closed = not has_layout_text(driver, "Inspect Input polish")
    shortcut_text = first_text_starting_with(driver, "Shortcuts ")

    driver.key_down("k", ctrl=True)
    reset_titles = visible_task_titles(driver)

    scroll_box = first_box(driver, "ScrollView")
    first_before = box_with_text(driver, "Runtime bridge")
    driver.wheel(scroll_box.x + 2, scroll_box.y + 2, 48)
    scrolled = box_with_text(driver, "Runtime bridge").y < first_before.y

    return TaskBoardBackendCandidateReplay(
        title=title,
        initial_frame=initial_frame,
        final_frame=driver.frame,
        filtered_titles=filtered_titles,
        modal_visible_after_click=modal_visible,
        modal_closed_after_escape=modal_closed,
        shortcut_text_after_escape=shortcut_text,
        reset_titles=reset_titles,
        scrolled=scrolled,
        final_focus=focused_box_summary(driver),
    )


def visible_task_titles(driver: NativeWindowDriver) -> tuple[str, ...]:
    return tuple(title for title in TASK_BOARD_TITLES if has_layout_text(driver, title))


def has_layout_text(driver: NativeWindowDriver, text: str) -> bool:
    return any(box.text == text for box in driver.surface.layout.boxes)


def first_text_starting_with(driver: NativeWindowDriver, prefix: str) -> str | None:
    for box in driver.surface.layout.boxes:
        if box.text is not None and box.text.startswith(prefix):
            return box.text
    return None


def box_with_text(driver: NativeWindowDriver, text: str):
    for box in driver.surface.layout.boxes:
        if box.text == text:
            return box
    raise KeyError(f"No native box with text {text!r}.")


def first_box(driver: NativeWindowDriver, name: str):
    for box in driver.surface.layout.boxes:
        if box.name == name:
            return box
    raise KeyError(f"No native box named {name!r}.")


def focused_box_summary(driver: NativeWindowDriver) -> tuple[str, str | None] | None:
    box = driver.surface.focused_box
    if box is None:
        return None
    return (box.name, box.text)


def summarize_headless_candidate_frame(
    driver: NativeWindowDriver,
    *,
    label: str,
) -> HeadlessCandidateFrameSummary:
    layout = driver.surface.layout
    paint = driver.paint
    return HeadlessCandidateFrameSummary(
        label=label,
        frame=driver.frame,
        size=driver.size,
        root_name=layout.root.name,
        focused=focused_box_summary(driver),
        layout_boxes=len(layout.boxes),
        paint_commands=len(paint.commands),
        visible_text=tuple(box.text for box in layout.boxes if box.text),
        paint_kinds=tuple(command.kind for command in paint.commands),
    )


def _format_run_report(label: str, report: HeadlessCandidateRunReport) -> str:
    return "\n".join(
        [
            f"{label}: {'passed' if report.passed else 'failed'}",
            f"  backend: {report.backend}",
            f"  title: {report.title}",
            f"  frame: {report.before.frame} -> {report.after.frame}",
            f"  size: {report.after.size[0]}x{report.after.size[1]}",
            f"  root: {report.after.root_name}",
            f"  focused: {_format_focus(report.after.focused)}",
            f"  layout boxes: {report.after.layout_boxes}",
            f"  paint commands: {report.after.paint_commands}",
            f"  visible text: {', '.join(report.after.visible_text)}",
        ]
    )


def _format_focus(focus: tuple[str, str | None] | None) -> str:
    if focus is None:
        return "none"
    name, text = focus
    return name if text is None else f"{name} {text!r}"


def _last_replay(backend: RecordingBackendCandidate, expected_type: type[Any]):
    replay = backend.replays[-1]
    if not isinstance(replay, expected_type):
        raise TypeError(f"Expected {expected_type.__name__}, got {type(replay).__name__}.")
    return replay


def _last_report(backend: HeadlessCandidateBackend) -> HeadlessCandidateRunReport:
    return backend.reports[-1]


if __name__ == "__main__":
    raise SystemExit(main())
