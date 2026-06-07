from __future__ import annotations

from dataclasses import dataclass

from .backend_candidate_apps import TASK_BOARD_TITLES


@dataclass(frozen=True)
class RendererCandidateCall:
    phase: str
    subject: str
    layout_boxes: int = 0
    paint_commands: int = 0
    boundary: str | None = None


@dataclass(frozen=True)
class RendererContractBoxSnapshot:
    path: tuple[int, ...]
    name: str
    bounds: tuple[int, int, int, int]
    text: str | None
    events: tuple[str, ...]
    state: tuple[str, ...]


@dataclass(frozen=True)
class RendererContractPaintSnapshot:
    kind: str
    path: tuple[int, ...]
    bounds: tuple[int, int, int, int]
    fill: str | None
    stroke: str | None
    stroke_width: int
    radius: int
    text: str | None
    color: str | None
    font_size: int
    clip: tuple[int, int, int, int] | None


@dataclass(frozen=True)
class RendererCandidateAcceptanceReport:
    renderer_backend: str
    headless: "HeadlessCandidateAcceptanceReport"
    calls: tuple[RendererCandidateCall, ...]

    @property
    def passed(self) -> bool:
        phases = {call.phase for call in self.calls}
        return (
            self.headless.passed
            and {"layout", "paint"} <= phases
            and any(call.layout_boxes > 0 for call in self.calls)
            and any(call.paint_commands > 0 for call in self.calls)
        )


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
    layout_snapshot: tuple[RendererContractBoxSnapshot, ...]
    paint_snapshot: tuple[RendererContractPaintSnapshot, ...]


@dataclass(frozen=True)
class HeadlessCandidateRunReport:
    backend: str
    renderer_backend: str
    title: str
    before: HeadlessCandidateFrameSummary
    after: HeadlessCandidateFrameSummary
    replay: object
    input_capabilities: tuple[str, ...]

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


@dataclass(frozen=True)
class LayoutOnlyCandidateAcceptanceReport:
    renderer_backend: str
    minimal: HeadlessCandidateRunReport
    task_board: HeadlessCandidateRunReport
    calls: tuple[RendererCandidateCall, ...]

    @property
    def passed(self) -> bool:
        phases = {call.phase for call in self.calls}
        return (
            self.minimal.passed
            and self.task_board.passed
            and {"layout", "paint"} <= phases
            and self.minimal.after.root_name == "ShortcutScope"
            and self.task_board.after.root_name == "ShortcutScope"
            and self.minimal.after.layout_boxes > 0
            and self.task_board.after.layout_boxes > 0
        )


@dataclass(frozen=True)
class LayoutOnlyTaskBoardStaticAcceptanceReport:
    renderer_backend: str
    frame: HeadlessCandidateFrameSummary
    calls: tuple[RendererCandidateCall, ...]

    @property
    def passed(self) -> bool:
        phases = {call.phase for call in self.calls}
        return (
            {"layout", "paint"} <= phases
            and self.frame.root_name == "ShortcutScope"
            and self.frame.size == (420, 257)
            and self.frame.focused == ("Input", "Search tasks")
            and self.frame.layout_boxes == 31
            and self.frame.paint_commands == 33
            and "Native Task Board" in self.frame.visible_text
            and "3 visible" in self.frame.visible_text
            and set(TASK_BOARD_TITLES) <= set(self.frame.visible_text)
            and "rect" in self.frame.paint_kinds
            and "text" in self.frame.paint_kinds
        )


@dataclass(frozen=True)
class ComposedRendererCandidateAcceptanceReport:
    renderer_backend: str
    layout_backend: str
    paint_backend: str
    raster_backend: str
    headless: HeadlessCandidateAcceptanceReport
    png_frame: HeadlessCandidateFrameSummary
    png_path: str
    layout_calls: tuple[RendererCandidateCall, ...]
    paint_calls: tuple[RendererCandidateCall, ...]
    raster_calls: tuple[RendererCandidateCall, ...]

    @property
    def passed(self) -> bool:
        return (
            self.headless.passed
            and self.png_frame.root_name == "ShortcutScope"
            and self.png_frame.layout_boxes > 0
            and self.png_frame.paint_commands > 0
            and any(
                call.phase == "layout" and call.layout_boxes > 0
                for call in self.layout_calls
            )
            and any(
                call.phase == "paint" and call.paint_commands > 0
                for call in self.paint_calls
            )
            and any(
                call.phase == "write_png" and call.paint_commands > 0
                for call in self.raster_calls
            )
        )
