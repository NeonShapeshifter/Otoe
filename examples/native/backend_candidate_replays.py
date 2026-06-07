from __future__ import annotations

from collections.abc import Callable
from typing import Any

from otoe import NativeWindowDriver, NativeWindowEvent

from .backend_candidate_apps import TASK_BOARD_TITLES
from .backend_candidate_snapshot_payloads import box_snapshot, paint_snapshot
from .backend_candidate_renderer_types import (
    HeadlessCandidateFrameSummary,
    HeadlessCandidateRunReport,
)
from .backend_candidate_replay_types import (
    MinimalBackendCandidateReplay,
    TaskBoardBackendCandidateReplay,
)


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
        event_count = driver.input_capability_event_count
        before = summarize_headless_candidate_frame(driver, label="before")
        replay = self._replay(driver, title=title)
        after = summarize_headless_candidate_frame(driver, label="after")
        self.reports.append(
            HeadlessCandidateRunReport(
                backend=self.name,
                renderer_backend=driver.surface.renderer_backend.name,
                title=title,
                before=before,
                after=after,
                replay=replay,
                input_capabilities=driver.input_capabilities_since(event_count),
            )
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

    driver.dispatch(NativeWindowEvent("key_down", key="Enter"))
    driver.dispatch(NativeWindowEvent("key_down", key="Tab"))

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
        layout_snapshot=tuple(box_snapshot(box) for box in layout.boxes),
        paint_snapshot=tuple(paint_snapshot(command) for command in paint.commands),
    )


def last_replay(backend: RecordingBackendCandidate, expected_type: type[Any]):
    replay = backend.replays[-1]
    if not isinstance(replay, expected_type):
        raise TypeError(
            f"Expected {expected_type.__name__}, got {type(replay).__name__}."
        )
    return replay


def last_report(backend: HeadlessCandidateBackend) -> HeadlessCandidateRunReport:
    return backend.reports[-1]
