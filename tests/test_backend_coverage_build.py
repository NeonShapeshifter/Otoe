from cli_helpers import (
    hashlib,
    json,
    os,
    subprocess,
    sys,
    main,
    _write_backend_capability_profile,
    _write_backend_coverage_requirements,
    _backend_coverage_test_hash,
    _refresh_manifest_artifact_hash,
)

def test_cli_build_writes_backend_coverage_artifact_from_profile_file(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "build_backend_coverage_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Build coverage')\n",
        encoding="utf-8",
    )
    requirements = tmp_path / "backend-requirements.json"
    _write_backend_coverage_requirements(requirements)
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[backend]\n"
        'name = "native"\n'
        'coverage_requirements = "backend-requirements.json"\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "coverage"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "build_backend_coverage_surface:app",
            "--profile-file",
            str(profile_file),
            "--out",
            str(output),
        ]
    )

    captured = capsys.readouterr()
    coverage_path = output / "otoe-backend-coverage.json"
    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert result == 0
    assert f"backend coverage artifact: {coverage_path}" in captured.out
    assert coverage["passed"] is True
    assert coverage["trace"] == {
        "candidateScope": {
            "level": "path0-render-tree-ir-v0",
        },
        "path0": {
            "renderTreeHash": _backend_coverage_test_hash("test-render-tree"),
            "layoutOutputHash": coverage["coverage"]["rendererBoundaries"][
                "evidenceMap"
            ]["renderTreeLayout"]["sources"][0]["boundaryProof"]["outputHash"],
            "paintOutputHash": coverage["coverage"]["rendererBoundaries"][
                "evidenceMap"
            ]["paint"]["sources"][0]["boundaryProof"]["outputHash"],
            "semanticValidation": {
                "passed": True,
                "errors": [],
            },
        },
    }
    assert manifest["backendCoverage"] == "otoe-backend-coverage.json"
    assert {
        "path": "otoe-backend-coverage.json",
        "size": coverage_path.stat().st_size,
        "sha256": hashlib.sha256(coverage_path.read_bytes()).hexdigest(),
    } in manifest["artifacts"]

def test_cli_build_runner_rejects_backend_coverage_trace_tampering(
    tmp_path,
    monkeypatch,
    capsys,
):
    app = tmp_path / "backend_coverage_trace_tamper_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Backend coverage trace tamper')\n",
        encoding="utf-8",
    )
    requirements = tmp_path / "backend-requirements.json"
    _write_backend_coverage_requirements(requirements)
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[runtime]\n"
        'files = ["backend_coverage_trace_tamper_app.py"]\n'
        "\n"
        "[backend]\n"
        'coverage_requirements = "backend-requirements.json"\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "backend-coverage-trace-tamper"
    monkeypatch.syspath_prepend(str(tmp_path))

    assert (
        main(
            [
                "build",
                "backend_coverage_trace_tamper_app:app",
                "--profile-file",
                str(profile_file),
                "--out",
                str(output),
                "--validate",
            ]
        )
        == 0
    )
    capsys.readouterr()

    coverage_path = output / "otoe-backend-coverage.json"
    original_coverage = json.loads(coverage_path.read_text(encoding="utf-8"))

    def verify_tamper(mutator, expected_error: str) -> None:
        coverage = json.loads(json.dumps(original_coverage))
        mutator(coverage)
        coverage_path.write_text(json.dumps(coverage, sort_keys=True), encoding="utf-8")
        _refresh_manifest_artifact_hash(output, "otoe-backend-coverage.json")

        verify = subprocess.run(
            [sys.executable, str(output / "otoe-run.py"), "--verify"],
            capture_output=True,
            cwd=output,
            env={**os.environ, "PYTHONPATH": ""},
            text=True,
        )

        assert verify.returncode == 1
        assert expected_error in verify.stderr

    verify_tamper(
        lambda coverage: coverage.pop("trace"),
        "otoe-backend-coverage.json: trace must be an object",
    )
    verify_tamper(
        lambda coverage: coverage["trace"]["path0"].__setitem__(
            "renderTreeHash",
            _backend_coverage_test_hash("wrong-render-tree"),
        ),
        "boundaryProof.renderTreeHash must match trace.path0.renderTreeHash",
    )
    verify_tamper(
        lambda coverage: coverage["trace"]["path0"].__setitem__(
            "renderTreeHash",
            "sha256:" + "a" * 63,
        ),
        "trace.path0.renderTreeHash must be a sha256 string",
    )
    verify_tamper(
        lambda coverage: coverage["trace"]["path0"].__setitem__(
            "layoutOutputHash",
            _backend_coverage_test_hash("wrong-layout"),
        ),
        "boundaryProof.outputHash must match trace.path0.layoutOutputHash",
    )
    verify_tamper(
        lambda coverage: coverage["trace"]["path0"].__setitem__(
            "paintOutputHash",
            _backend_coverage_test_hash("wrong-paint"),
        ),
        "boundaryProof.outputHash must match trace.path0.paintOutputHash",
    )
    verify_tamper(
        lambda coverage: coverage["trace"]["path0"].pop("semanticValidation"),
        "trace.path0.semanticValidation must be an object",
    )
    verify_tamper(
        lambda coverage: coverage["readiness"]["candidate"].__setitem__(
            "backend",
            "totally-fake-backend",
        ),
        "backend must match readiness.candidate.backend",
    )
    verify_tamper(
        lambda coverage: coverage["coverage"]["widgets"]["evidenceMap"]["Text"][
            "sources"
        ][0]["capabilityProof"].__setitem__(
            "auditHash",
            "sha256:" + "A" * 64,
        ),
        "coverage.widgets.evidenceMap.Text.sources[0].capabilityProof.auditHash "
        "must be a sha256 string",
    )
    verify_tamper(
        lambda coverage: coverage["trace"]["path0"]["semanticValidation"].__setitem__(
            "passed",
            False,
        ),
        "trace.path0.semanticValidation.passed must be true",
    )
    verify_tamper(
        lambda coverage: coverage["trace"]["path0"]["semanticValidation"].__setitem__(
            "errors",
            ["semantic drift"],
        ),
        "trace.path0.semanticValidation.errors must be []",
    )

def test_cli_build_fails_for_invalid_backend_coverage_without_manifest(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "invalid_backend_coverage_build_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Invalid backend coverage')\n",
        encoding="utf-8",
    )
    requirements = tmp_path / "backend-requirements.json"
    _write_backend_coverage_requirements(requirements, widgets=("Text", "Button"))
    profile_json = tmp_path / "candidate-profile.json"
    _write_backend_capability_profile(
        profile_json,
        name="candidate-build-coverage-failure",
        widgets={"Text": "text"},
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[backend]\n"
        'name = "native"\n'
        'capability_profile = "candidate-profile.json"\n'
        'coverage_requirements = "backend-requirements.json"\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "invalid-backend-coverage"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "invalid_backend_coverage_build_surface:app",
            "--profile-file",
            str(profile_file),
            "--out",
            str(output),
        ]
    )

    captured = capsys.readouterr()
    coverage = json.loads(
        (output / "otoe-backend-coverage.json").read_text(encoding="utf-8")
    )
    assert result == 1
    assert coverage["passed"] is False
    assert coverage["coverage"]["widgets"]["missing"] == ["Button"]
    assert not (output / "manifest.json").exists()
    assert (
        "build: backend coverage invalid; refusing to write build manifest"
        in captured.err
    )

