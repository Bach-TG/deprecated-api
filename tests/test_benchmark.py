"""Cheap regression checks; no model downloads or API requests."""

import json
from pathlib import Path

import pytest

from deprecated_api.annotation import label, postprocess
from deprecated_api.dataset import load_benchmark
from deprecated_api.evaluation import cost_table, summarize
from deprecated_api.proposed import (
    APIKnowledgeBase,
    check_api,
    configure_verifier,
    verifier_iterative_method,
    verifier_one_shot_method,
    verify_and_repair,
)
from deprecated_api.runner import baseline_method, done_ids, run_experiments


@pytest.fixture
def mappings():
    # Literal examples from the supplied mappings.json (not sample gold fields).
    rows = [
        {"lib": "numpy", "deprecated": "numpy.product", "replacement": "numpy.prod"},
        {"lib": "numpy", "deprecated": "numpy.alltrue", "replacement": "numpy.all"},
        {
            "lib": "pandas",
            "deprecated": "pandas.DataFrame.iteritems",
            "replacement": "pandas.DataFrame.items",
        },
        {"lib": "pytorch", "deprecated": "torch.svd", "replacement": "torch.linalg.svd"},
    ]
    configure_verifier(rows)
    return rows


@pytest.fixture
def sample():
    return {
        "id": "numpy-outdated-test",
        "lib": "numpy",
        "category": "outdated",
        "probing input": "def f(x):\n",
        "reference dict": {},
        "alias dict": {"np.product": "numpy.product"},
        "deprecated api": ["numpy.product"],
        "replacement api": "numpy.prod",
    }


def scripted(*texts):
    calls = []

    def generate(prompt, mode, max_new_tokens=None, instruction=None):
        calls.append((prompt, mode, instruction))
        return {
            "text": texts[len(calls) - 1],
            "finish_reason": "STOP",
            "tok_in": 10 * len(calls),
            "tok_out": 3 * len(calls),
            "tok_think": len(calls),
            "latency_ms": 2.5 * len(calls),
        }

    return generate, calls


def test_baseline_schema_and_annotation(sample):
    gen, calls = scripted("```python\nreturn np.product(x)\n```", "    return np.prod(x)\n")
    row = baseline_method(sample, gen, "chat")
    assert set(row) == {
        "completion",
        "apis",
        "label",
        "raw",
        "finish_reason",
        "tok_in",
        "tok_out",
        "tok_think",
        "latency_ms",
    }
    assert row["completion"] == "return np.product(x)"
    assert row["apis"] == ["numpy.product"]
    assert row["label"] == "DepC"
    assert calls == [(sample["probing input"], "chat", None)]
    assert baseline_method(sample, gen, "raw")["label"] == "RepC"
    # The original extractor intentionally sees only the first statement.
    _, apis = postprocess(sample, "x = 1\nreturn np.product(x)", "chat")
    assert apis == []
    assert label(sample, ["numpy.prod", "numpy.product"]) == "DepC"


def test_mapping_statuses(mappings):
    assert check_api("numpy.product", "numpy")["replacement"] == "numpy.prod"
    assert check_api("pandas.DataFrame.iteritems", "pandas")["status"] == "deprecated"
    assert check_api("torch.svd", "pytorch")["replacement"] == "torch.linalg.svd"
    assert check_api("numpy.prod", "numpy")["status"] == "active"
    assert check_api("numpy.made_up", "numpy")["status"] == "unknown"
    assert check_api("numpy.product", "pandas")["status"] == "unknown"
    with pytest.raises(ValueError, match="no version fields"):
        check_api("numpy.product", "numpy", "2.0")


@pytest.mark.parametrize("text", ["return np.prod(x)", "return custom(x)", "return x"])
@pytest.mark.parametrize("method", [verifier_one_shot_method, verifier_iterative_method])
def test_no_issue_no_repair(mappings, sample, text, method):
    generate, calls = scripted(text)
    row = method(sample, generate, "chat")
    assert len(calls) == row["num_calls"] == 1
    assert row["repair_rounds"] == 0
    assert row["completion"] == row["initial_completion"] == text
    assert row["issues"] == []


@pytest.mark.parametrize(
    "method,rounds",
    [
        (verifier_one_shot_method, 1),
        (verifier_iterative_method, 2),
    ],
)
def test_bounded_repairs_and_totals(mappings, sample, method, rounds):
    generate, calls = scripted(*(["return np.product(x)"] * (rounds + 1)))
    row = method(sample, generate, "chat")
    assert row["repair_rounds"] == rounds
    assert row["num_calls"] == len(calls) == rounds + 1
    multiplier = sum(range(1, rounds + 2))
    assert row["tok_in"] == 10 * multiplier
    assert row["tok_out"] == 3 * multiplier
    assert row["tok_think"] == multiplier
    assert row["latency_ms"] == 2.5 * multiplier
    assert len(row["trace"]) == rounds + 1
    assert row["final_issues"][0]["status"] == "deprecated"
    assert row["label"] == "DepC"
    assert all(mode == "chat" for _, mode, _ in calls)
    assert all(instruction == "{code}" for _, _, instruction in calls[1:])


def test_iterative_rechecks_stops_and_lists_multiple_issues(mappings, sample):
    generate, calls = scripted("return np.product(x) + np.alltrue(x)", "return np.prod(x)")
    row = verifier_iterative_method(sample, generate, "chat")
    assert row["repair_rounds"] == 1
    assert row["label"] == "RepC"
    assert row["final_issues"] == []
    assert calls[1][0].index("- numpy.alltrue") < calls[1][0].index("- numpy.product")
    assert "replacement: numpy.all" in calls[1][0]
    assert "replacement: numpy.prod" in calls[1][0]


def test_generation_is_independent_of_gold(mappings, sample):
    # Adversarial gold labels change evaluation only, never repair decisions/prompts.
    other = {
        **sample,
        "deprecated api": ["gold_secret"],
        "replacement api": "gold_other",
        "function": "gold_function",
        "reference": "gold_reference",
    }
    gen1, calls1 = scripted("return np.product(x)", "return np.prod(x)")
    gen2, calls2 = scripted("return np.product(x)", "return np.prod(x)")
    row1 = verifier_one_shot_method(sample, gen1, "chat")
    row2 = verifier_one_shot_method(other, gen2, "chat")
    assert calls1 == calls2
    assert row1["trace"] == row2["trace"]
    assert row1["label"] == "RepC" and row2["label"] == "Others"
    context = {k: sample[k] for k in ("probing input", "reference dict", "alias dict", "lib")}
    gen, _ = scripted("return np.prod(x)")
    assert "label" not in verify_and_repair(context, gen, "chat", 1)
    with pytest.raises(ValueError, match="chat mode only"):
        verifier_one_shot_method(sample, gen, "raw")


def test_checkpoint_resume_including_errors(sample, tmp_path):
    generate, calls = scripted("return np.product(x)", "return np.prod(x)")
    items = [sample, {**sample, "id": "second"}]
    runs, methods = [("deepseek", "chat")], {"baseline": baseline_method}

    def get_generate(_):
        return generate

    run_experiments(items[:1], runs, methods, tmp_path, get_generate)
    results = run_experiments(items, runs, methods, tmp_path, get_generate)
    assert len(calls) == 2
    assert len(results[("baseline", "deepseek", "chat")]) == 2
    path = tmp_path / "baseline/results_deepseek_chat.jsonl"
    assert done_ids(path) == {sample["id"], "second"}
    with path.open("a") as f:
        f.write(json.dumps({"id": "error", "label": "Error"}) + "\n")
    run_experiments([*items, {**sample, "id": "error"}], runs, methods, tmp_path, get_generate)
    assert len(calls) == 2


def test_original_metric_denominators_and_cost():
    rows = [
        {
            "lib": "numpy",
            "category": category,
            "label": lab,
            "num_calls": 3,
            "tok_in": 30,
            "latency_ms": 6,
        }
        for category, lab in [
            ("outdated", "DepC"),
            ("outdated", "RepC"),
            ("up-to-dated", "Others"),
            ("up-to-dated", "Error"),
        ]
    ]
    s = summarize(rows)
    assert s["All"] == {"n": 3, "AUP": 2 / 3, "DUR": 1 / 2}
    assert s["O"] == {"n": 2, "AUP": 1, "DUR": 1 / 2}
    assert s["U"] == {"n": 1, "AUP": 0, "DUR": None}
    assert s["errors_U"] == 1
    key = ("baseline", "deepseek", "raw")
    assert cost_table({key: rows}, [("deepseek", "raw")])[key]["calls"] == 4


def test_real_benchmark_data():
    if not Path("data/raw/mappings.json").exists():
        pytest.skip("local benchmark dataset is not distributed with source")
    mappings, items, humaneval = load_benchmark("smoke")
    assert len(mappings) == 145
    assert len(items) == 32
    assert len(humaneval) == 164
    assert {key for row in mappings for key in row} == {"lib", "deprecated", "replacement"}
    kb = APIKnowledgeBase(mappings)
    for row in mappings:
        checked = kb.check_api(row["deprecated"], row["lib"])
        assert checked["status"] == "deprecated"
        assert checked["replacement"] == row["replacement"]
    _, capped, _ = load_benchmark("sample", limit=1)
    _, repeated, _ = load_benchmark("sample", limit=1)
    assert capped == repeated
    assert len({(row["lib"], row["category"]) for row in capped}) == len(capped)
