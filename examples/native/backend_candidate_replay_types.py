from __future__ import annotations

from dataclasses import dataclass

from .backend_candidate_apps import TASK_BOARD_TITLES


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
