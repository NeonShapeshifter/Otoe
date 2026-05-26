from __future__ import annotations

from pathlib import Path

from examples.live_server import LivePreviewStylesheet


ROOT = Path(__file__).resolve().parents[1]
REFERENCE_THEME_CSS_PATH = ROOT / "preview" / "reference_theme.css"
REFERENCE_THEME_STYLESHEET = LivePreviewStylesheet(
    route="/reference_theme.css",
    path=REFERENCE_THEME_CSS_PATH,
)

