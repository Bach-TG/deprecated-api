"""Original method schema and append/flush/ID-resume runner."""

import json
import os
import time
from pathlib import Path

from .annotation import label, postprocess
from .backends import get_generate_fn


def baseline_method(sample, generate, mode):
    comp = generate(sample["probing input"], mode)
    completion, apis = postprocess(sample, comp["text"], mode)
    return {
        "completion": completion,
        "apis": apis,
        "label": label(sample, apis),
        "raw": comp["text"],
        "finish_reason": comp["finish_reason"],
        "tok_in": comp["tok_in"],
        "tok_out": comp["tok_out"],
        "tok_think": comp["tok_think"],
        "latency_ms": comp["latency_ms"],
    }


METHODS = {"baseline": baseline_method}


def result_path(method_name, model_name, mode, results_dir):
    d = os.path.join(results_dir, method_name)
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, f"results_{model_name}_{mode}.jsonl")


def done_ids(path):
    if not os.path.exists(path):
        return set()
    with open(path, encoding="utf-8") as f:
        return {json.loads(line)["id"] for line in f if line.strip()}


def read_results(items, runs, methods, results_dir):
    all_results = {}
    for model_name, mode in runs:
        for method_name in methods:
            path = Path(results_dir) / method_name / f"results_{model_name}_{mode}.jsonl"
            if not os.path.exists(path):
                continue
            with open(path, encoding="utf-8") as f:
                rows = [json.loads(line) for line in f if line.strip()]
            wanted = {it["id"] for it in items}
            all_results[(method_name, model_name, mode)] = [r for r in rows if r["id"] in wanted]
    return all_results


def run_experiments(items, runs, methods, results_dir, get_generate=get_generate_fn):
    for model_name, mode in runs:
        try:
            generate = get_generate(model_name)
        except Exception as e:
            print(f"skipping all methods for {model_name}/{mode}: {e!r}")
            continue

        for method_name, method_fn in methods.items():
            supported = getattr(method_fn, "supported_modes", ("raw", "chat"))
            if mode not in supported:
                print(f"skipping unsupported {method_name}/{model_name}/{mode}")
                continue
            path = result_path(method_name, model_name, mode, results_dir)
            done = done_ids(path)
            todo = [it for it in items if it["id"] not in done]
            print(
                f"\n=== {method_name}/{model_name}/{mode} === "
                f"({len(done)} already done, {len(todo)} to run)"
            )

            started = time.time()
            with open(path, "a", encoding="utf-8") as f:
                for i, sample in enumerate(todo, 1):
                    try:
                        out = method_fn(sample, generate, mode)
                        row = {
                            "id": sample["id"],
                            "lib": sample["lib"],
                            "category": sample["category"],
                            **out,
                        }
                    except Exception as e:
                        row = {
                            "id": sample["id"],
                            "lib": sample["lib"],
                            "category": sample["category"],
                            "completion": "",
                            "apis": [],
                            "label": "Error",
                            "error": repr(e),
                        }
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
                    f.flush()
                    if i % 20 == 0 or i == len(todo):
                        print(f"  {i}/{len(todo)} done ({time.time() - started:.0f}s elapsed)")
    return read_results(items, runs, methods, results_dir)
