from pathlib import Path


import examples.native.backend_candidate_acceptance as backend_candidate_acceptance
import examples.native.backend_candidate_cli as backend_candidate_cli
import examples.native.backend_candidate_skeleton as backend_candidate_skeleton


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

def test_backend_candidate_skeleton_keeps_compatibility_facade():
    assert backend_candidate_skeleton.main is backend_candidate_cli.main
    assert (
        backend_candidate_skeleton.run_headless_candidate_acceptance
        is backend_candidate_acceptance.run_headless_candidate_acceptance
    )
    assert (
        backend_candidate_skeleton.backend_readiness_report_to_dict
        is backend_candidate_acceptance.backend_readiness_report_to_dict
    )
