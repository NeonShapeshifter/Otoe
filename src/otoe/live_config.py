from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


class LivePreviewApp(Protocol):
    def render_fragment(self) -> str:
        raise NotImplementedError

    def dispatch_event(self, event_id: str, *args: Any) -> str:
        raise NotImplementedError


class DisposableLivePreviewApp(Protocol):
    """Optional lifecycle capability for live-preview applications."""

    def dispose(self) -> None:
        raise NotImplementedError


@dataclass(frozen=True)
class LivePreviewStylesheet:
    route: str
    path: Path | None


@dataclass(frozen=True)
class LivePreviewConfig:
    title: str
    css_route: str
    css_path: Path | None
    root_class: str = ""
    extra_css: tuple[LivePreviewStylesheet, ...] = ()

    def stylesheets(self) -> tuple[LivePreviewStylesheet, ...]:
        return (
            *self.extra_css,
            LivePreviewStylesheet(route=self.css_route, path=self.css_path),
        )

    def stylesheet_for(self, route: str) -> LivePreviewStylesheet | None:
        for stylesheet in self.stylesheets():
            if stylesheet.route == route:
                return stylesheet
        return None
