"""Small file contracts between the three notebooks; no notebook state sharing."""

import json
import os
from pathlib import Path

from . import backends
from .artifacts import find_input, stage_dir, write_manifest
from .config import ARTIFACTS_DIR, IS_KAGGLE
from .dataset import load_benchmark
from .runner import baseline_method, read_results, run_experiments

BASELINE_RAW_STAGE = "00_baseline_raw"
BASELINE_CHAT_STAGE = "00_baseline_chat"
PROPOSED_ONE_SHOT_STAGE = "01_verifier_one_shot"
PROPOSED_ITERATIVE_STAGE = "01_verifier_iterative"
EVALUATE_STAGE = "02_evaluate"
PROPOSED_NAMES = ("verifier_one_shot", "verifier_iterative")
DEFAULT_SPLIT = os.environ.get("DEPAPI_SPLIT", "full")
DEFAULT_RUNS = (("deepseek", "raw"), ("deepseek", "chat"))


def make_run_config(
    split=DEFAULT_SPLIT, limit=0, sample_seed=42, runs=None, humaneval_limit=20
):
    return {
        "split": split,
        "limit": limit,
        "sample_seed": sample_seed,
        "runs": [
            list(run)
            for run in (
                runs
                if runs is not None
                else DEFAULT_RUNS
            )
        ],
        "model_identifiers": {
            "deepseek": backends.DEEPSEEK_MODEL,
            "gemini": os.environ.get("GEMINI_MODEL", backends.GEMINI_MODEL),
        },
        "gemini_thinking_level": backends.GEMINI_THINKING_LEVEL,
        "max_new_tokens": backends.MAX_NEW_TOKENS,
        "gemini_pacing_secs": backends.GEMINI_PACING_SECS,
        "humaneval_limit": humaneval_limit,
    }


def apply_run_config(config):
    """Apply recorded model settings when an evaluation control needs them."""
    if config["model_identifiers"]["deepseek"] != backends.DEEPSEEK_MODEL:
        raise ValueError("Stage 00 DeepSeek model differs from the bundled backend")
    backends.MAX_NEW_TOKENS = config["max_new_tokens"]
    backends.GEMINI_PACING_SECS = config["gemini_pacing_secs"]
    backends.GEMINI_THINKING_LEVEL = config.get(
        "gemini_thinking_level", backends.GEMINI_THINKING_LEVEL
    )
    os.environ["GEMINI_MODEL"] = config["model_identifiers"]["gemini"]


def upstream_dir(stage):
    try:
        if IS_KAGGLE:
            return find_input(f"artifacts/{stage}/run_config.json").parent
        path = ARTIFACTS_DIR / stage
        if not (path / "run_config.json").is_file():
            raise FileNotFoundError(path / "run_config.json")
        return path
    except FileNotFoundError as e:
        raise FileNotFoundError(
            f"Missing {stage}/run_config.json. Run {stage} first; on Kaggle attach "
            f"the {stage} notebook's saved output as a kernel source. "
            "Also attach the benchmark dataset to every stage."
        ) from e


def read_run_config(directory):
    return json.loads((Path(directory) / "run_config.json").read_text(encoding="utf-8"))


def prepare_stage(stage, config):
    output = stage_dir(stage)
    path = output / "run_config.json"
    if path.exists() and read_run_config(output) != config:
        raise ValueError(
            f"{path} differs from this configuration. Archive the existing stage artifacts "
            "before starting a different experiment; do not mix checkpoint IDs across splits."
        )
    path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    publish_stage(stage)
    return output


def run_baseline_stage(stage, selected_runs):
    """Run only the selected baseline mode(s) under a mode-specific artifact stage.

    Every split baseline output records the same complete experiment config;
    ``selected_runs`` describes the subset generated in this Kaggle execution.
    """
    selected_runs = [tuple(run) for run in selected_runs]
    planned_runs = {tuple(run) for run in DEFAULT_RUNS}
    if not selected_runs or not set(selected_runs).issubset(planned_runs):
        raise ValueError(
            f"selected_runs must be a non-empty subset of DEFAULT_RUNS={DEFAULT_RUNS}"
        )
    config = make_run_config(split=DEFAULT_SPLIT, runs=DEFAULT_RUNS)
    output = prepare_stage(stage, config)
    _, items, _ = load_benchmark(config["split"], config["limit"], config["sample_seed"])
    results = run_experiments(
        items, selected_runs, {"baseline": baseline_method}, output / "results"
    )
    publish_stage(stage, methods=["baseline"], selected_runs=selected_runs)
    return config, results


def run_baseline_mode(mode):
    """Run one DeepSeek baseline mode, keeping raw/chat artifacts separate."""
    stages = {"raw": BASELINE_RAW_STAGE, "chat": BASELINE_CHAT_STAGE}
    if mode not in stages:
        raise ValueError(f"BASELINE_MODE must be 'raw' or 'chat', got {mode!r}")
    return run_baseline_stage(stages[mode], [("deepseek", mode)])


def run_proposed_mode(method_name):
    """Run one verifier under its own artifact stage and resumable checkpoint."""
    stages = {
        "verifier_one_shot": PROPOSED_ONE_SHOT_STAGE,
        "verifier_iterative": PROPOSED_ITERATIVE_STAGE,
    }
    if method_name not in stages:
        raise ValueError(f"PROPOSED_MODE must be one of {PROPOSED_NAMES}, got {method_name!r}")

    from .proposed import configure_verifier
    from .runner import METHODS

    config = make_run_config(split=DEFAULT_SPLIT, runs=DEFAULT_RUNS)
    chat_runs = [tuple(run) for run in config["runs"] if run[1] == "chat"]
    if not chat_runs:
        raise ValueError("DEFAULT_RUNS must include at least one chat run for proposed methods")
    output = prepare_stage(stages[method_name], config)
    mappings, items, _ = load_benchmark(config["split"], config["limit"], config["sample_seed"])
    configure_verifier(mappings)
    results = run_experiments(
        items, chat_runs, {method_name: METHODS[method_name]}, output / "results"
    )
    publish_stage(stages[method_name], methods=[method_name], supported_modes=["chat"])
    return config, results


def publish_stage(stage, **extra):
    output = stage_dir(stage)
    files = {
        str(path.relative_to(output)): path.relative_to(output)
        for path in sorted(output.rglob("*"))
        if path.is_file() and path.name != "manifest.json"
    }
    return write_manifest(stage, files, **extra)


def load_chained_results(items):
    baseline_raw = upstream_dir(BASELINE_RAW_STAGE)
    baseline_chat = upstream_dir(BASELINE_CHAT_STAGE)
    proposed_one_shot = upstream_dir(PROPOSED_ONE_SHOT_STAGE)
    proposed_iterative = upstream_dir(PROPOSED_ITERATIVE_STAGE)
    config = read_run_config(baseline_raw)
    other_configs = {
        BASELINE_CHAT_STAGE: read_run_config(baseline_chat),
        PROPOSED_ONE_SHOT_STAGE: read_run_config(proposed_one_shot),
        PROPOSED_ITERATIVE_STAGE: read_run_config(proposed_iterative),
    }
    if any(config != other for other in other_configs.values()):
        differing = sorted(
            key for other in other_configs.values()
            for key in set(config) | set(other)
            if config.get(key) != other.get(key)
        )
        differing = sorted(set(differing))
        raise ValueError(
            "Run configs for baseline/proposed artifacts differ in "
            f"{differing}; run each mode with matching settings before evaluating."
        )
    runs = [tuple(run) for run in config["runs"]]
    raw_runs = [run for run in runs if run[1] == "raw"]
    chat_runs = [run for run in runs if run[1] == "chat"]
    results = read_results(items, raw_runs, ["baseline"], baseline_raw / "results")
    results.update(read_results(items, chat_runs, ["baseline"], baseline_chat / "results"))
    proposed_chat_runs = [run for run in runs if run[1] == "chat"]
    results.update(read_results(
        items, proposed_chat_runs, ["verifier_one_shot"], proposed_one_shot / "results"
    ))
    results.update(read_results(
        items, proposed_chat_runs, ["verifier_iterative"], proposed_iterative / "results"
    ))
    for method in ("baseline", *PROPOSED_NAMES):
        if not any(key[0] == method and rows for key, rows in results.items()):
            raise FileNotFoundError(f"No {method} results found in the attached stage artifacts")
    return config, results


def write_keyed_results(path, results):
    """Serialize tuple-keyed reports without changing their values."""
    records = [
        {"method": key[0], "model": key[1], "mode": key[2], **value}
        for key, value in results.items()
    ]
    Path(path).write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
