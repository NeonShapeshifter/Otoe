from examples.saas.preview import build_preview_html


def test_saas_preview_builder_contains_product_surfaces():
    html = build_preview_html()

    assert "<!doctype html>" in html
    assert "LumaOps" in html
    assert "Customer pipeline" in html
    assert "$88,300" in html
    assert "Northstar Analytics" in html
    assert "Customer health" in html
    assert "SaaSOverview" not in html
