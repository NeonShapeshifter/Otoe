import json
from pathlib import Path


from examples.native.backend_candidate_skeleton import (
    main,
)


COMPOSED_RENDERER_COMPACT_CONTRACT_FIXTURE = Path(
    "examples/native/contracts/composed_renderer_compact_expected.json"
)
STYLE_OPS_CONTRACT_FIXTURE = Path("examples/native/contracts/style_ops_expected.json")
RENDER_TREE_CONTRACT_FIXTURE = Path(
    "examples/native/contracts/render_tree_expected.json"
)
BUNDLE_STYLE_OPS_CONTRACT_FIXTURE = Path(
    "examples/native/contracts/bundle_style_ops_expected.json"
)
BACKEND_READINESS_CONTRACT_FIXTURE = Path(
    "examples/native/contracts/backend_readiness_expected.json"
)
BACKEND_COVERAGE_DECLARATION_FIXTURE = Path(
    "examples/native/contracts/backend_coverage_full_declaration.json"
)
BACKEND_CANDIDATE_PARTIAL_PROFILE_FIXTURE = Path(
    "examples/native/contracts/backend_candidate_partial_profile.json"
)

def test_backend_candidate_skeleton_main_writes_contract_json_artifact(
    tmp_path,
    capsys,
):
    output = tmp_path / "artifacts" / "renderer-contract.json"

    result = main(
        [
            "--renderer-contract-json",
            "--compact-contract",
            "--contract-out",
            str(output),
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert result == 0
    assert captured.out == f"contract artifact: {output}\n"
    assert payload["schemaVersion"] == 1
    assert payload["format"] == "renderer-contract-compact"
    assert payload["rendererBackend"] == "recording-renderer-candidate"
