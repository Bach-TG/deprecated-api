"""Execute canonical stage cells in fresh namespaces with a scripted backend.

This tests file chaining using the real smoke dataset, not LLM quality. It never
downloads DeepSeek or calls Gemini. Notebook files are read-only here.
"""

import json
from pathlib import Path

import matplotlib
import pytest

from deprecated_api import artifacts, backends, config, pipeline

matplotlib.use("Agg")
ROOT = Path(__file__).resolve().parents[1]


def execute_stage(name):
    notebook = json.loads((ROOT / "notebooks" / f"{name}.ipynb").read_text())
    namespace = {"__name__": "__main__"}
    for i, cell in enumerate(notebook["cells"]):
        if cell["cell_type"] == "code":
            exec(compile("".join(cell["source"]), f"{name}:cell{i}", "exec"), namespace)
    return namespace


def test_split_baseline_pipeline_smoke(monkeypatch, tmp_path, capsys):
    if not (ROOT / "data/raw/smoke.json").exists():
        pytest.skip("local benchmark dataset is not distributed with source")
    monkeypatch.setenv("DEPAPI_SPLIT", "smoke")
    monkeypatch.setattr(pipeline, "DEFAULT_SPLIT", "smoke")
    monkeypatch.setattr(artifacts, "ARTIFACTS_DIR", tmp_path / "artifacts")
    monkeypatch.setattr(pipeline, "ARTIFACTS_DIR", tmp_path / "artifacts")
    monkeypatch.setattr(config, "FIGURES_DIR", tmp_path / "reports/figures")
    calls = []

    def generate(prompt, mode, max_new_tokens=None, instruction=None):
        calls.append((mode, instruction))
        text = "    return numpy.prod(x)" if instruction else "    return numpy.product(x)"
        return {
            "text": text,
            "finish_reason": "STOP",
            "tok_in": 10,
            "tok_out": 4,
            "tok_think": 0,
            "latency_ms": 1.5,
        }

    def no_gemini():
        raise RuntimeError("Gemini disabled in offline smoke test")

    monkeypatch.setattr(backends, "_loaded", {"deepseek": generate})
    monkeypatch.setattr(backends, "load_gemini", no_gemini)
    # Run each verifier independently from the baseline and from one another.
    monkeypatch.setenv("DEPAPI_PROPOSED_MODE", "verifier_one_shot")
    execute_stage("01_proposed_methods")
    monkeypatch.setenv("DEPAPI_BASELINE_MODE", "raw")
    execute_stage("00_baseline")
    monkeypatch.setenv("DEPAPI_BASELINE_MODE", "chat")
    execute_stage("00_baseline")
    monkeypatch.setenv("DEPAPI_PROPOSED_MODE", "verifier_iterative")
    execute_stage("01_proposed_methods")
    evaluated = execute_stage("02_evaluate")
    keys = set(evaluated["all_results"])
    assert keys == {
        ("baseline", "deepseek", "raw"),
        ("baseline", "deepseek", "chat"),
        ("verifier_one_shot", "deepseek", "chat"),
        ("verifier_iterative", "deepseek", "chat"),
    }
    assert all(len(rows) == 32 for rows in evaluated["all_results"].values())
    assert all(
        row["label"] != "Error" for rows in evaluated["all_results"].values() for row in rows
    )
    for stage in (
        "00_baseline_raw",
        "00_baseline_chat",
        "01_verifier_one_shot",
        "01_verifier_iterative",
        "02_evaluate",
    ):
        stage_path = tmp_path / "artifacts" / stage
        assert (stage_path / "run_config.json").is_file()
        manifest = json.loads((stage_path / "manifest.json").read_text())
        assert all((stage_path / path).is_file() for path in manifest["files"].values())
    before = len(calls)
    monkeypatch.setenv("DEPAPI_BASELINE_MODE", "raw")
    execute_stage("00_baseline")
    monkeypatch.setenv("DEPAPI_BASELINE_MODE", "chat")
    execute_stage("00_baseline")
    monkeypatch.setenv("DEPAPI_PROPOSED_MODE", "verifier_one_shot")
    execute_stage("01_proposed_methods")
    monkeypatch.setenv("DEPAPI_PROPOSED_MODE", "verifier_iterative")
    execute_stage("01_proposed_methods")
    assert len(calls) == before
    comparison = capsys.readouterr().out
    assert all(name in comparison for name in ("baseline", *pipeline.PROPOSED_NAMES))
    assert (tmp_path / "reports/figures/02_evaluate/comparison.png").is_file()


def test_kaggle_chaining_without_generated_mount_names(monkeypatch, tmp_path):
    monkeypatch.setattr(artifacts, "IS_KAGGLE", True)
    monkeypatch.setattr(artifacts, "INPUT_DIR", tmp_path)
    monkeypatch.setattr(pipeline, "IS_KAGGLE", True)
    with pytest.raises(FileNotFoundError, match="attach"):
        pipeline.upstream_dir("00_baseline")
    upstream = tmp_path / "arbitrary-kaggle-mount/artifacts/00_baseline"
    upstream.mkdir(parents=True)
    (upstream / "run_config.json").write_text("{}")
    assert pipeline.upstream_dir("00_baseline") == upstream


def test_find_input_nested_kaggle_dataset_layout(monkeypatch, tmp_path):
    monkeypatch.setattr(artifacts, "IS_KAGGLE", True)
    monkeypatch.setattr(artifacts, "INPUT_DIR", tmp_path / "input")
    dataset = tmp_path / "input/datasets/bachtruonggia/deprecated-api-input"
    dataset.mkdir(parents=True)
    mappings = dataset / "mappings.json"
    mappings.write_text("[]")

    assert artifacts.find_input("mappings.json") == mappings


def test_config_resume_guard(monkeypatch, tmp_path):
    monkeypatch.setattr(artifacts, "ARTIFACTS_DIR", tmp_path)
    original = pipeline.make_run_config("smoke")
    pipeline.prepare_stage("00_baseline_raw", original)
    with pytest.raises(ValueError, match="Archive"):
        pipeline.prepare_stage("00_baseline_raw", {**original, "split": "full"})


def test_gemini_configuration_defaults_and_chaining():
    config = pipeline.make_run_config("smoke", runs=[("gemini", "chat")])
    assert config["model_identifiers"]["gemini"] == "gemini-3.1-flash-lite"
    assert config["gemini_thinking_level"] == "minimal"
    pipeline.apply_run_config(config)
    assert backends.GEMINI_THINKING_LEVEL == "minimal"
