from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_native_layout_v0_decision_is_documented_and_linked():
    adr = (ROOT / "ADR-020-native-layout-v0-v1-decision.md").read_text(
        encoding="utf-8"
    )
    doc = (ROOT / "docs" / "native-layout.md").read_text(encoding="utf-8")
    native_status = (ROOT / "docs" / "native-status.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "**Status:** Accepted" in adr
    assert "**Date:** June 10, 2026" in adr
    assert "Otoe layout v0 remains the existing Python stack layout engine." in adr
    assert "Layout v1 is a future decision." in adr
    assert "Required Acceptance Bar For Layout v1" in adr

    for phrase in (
        "flex grow/shrink",
        "wrapping",
        "percentages or `auto` dimensions",
        "CSS grid",
        "absolute/fixed positioning",
        "margin geometry",
    ):
        assert phrase in doc

    assert "ADR-020" in native_status
    assert "docs/native-layout.md" in readme
    assert "ADR-020-native-layout-v0-v1-decision.md" in readme
