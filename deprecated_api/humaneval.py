"""Original HumanEval model/mode control (not a verifier intervention test)."""

import os as _os
import subprocess
import sys
import tempfile
import time

from .annotation import strip_fences
from .evaluation import pct

HUMANEVAL_MAX_NEW_TOKENS = 384
HUMANEVAL_TIMEOUT_SECS = 10
HE_CHAT_INSTRUCTION = (
    "Complete the following Python function. "
    "Output only the complete function's code, no explanation.\n\n{code}"
)


def build_program(problem, mode, completion):
    if mode == "raw":
        body = problem["prompt"] + completion
    else:
        body = strip_fences(completion)
    return f"{body}\n\n{problem['test']}\n\ncheck({problem['entry_point']})\n"


def run_program(program):
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(program)
        path = f.name
    try:
        proc = subprocess.run(
            [sys.executable, path], capture_output=True, text=True, timeout=HUMANEVAL_TIMEOUT_SECS
        )
        return proc.returncode == 0, (proc.stderr or "")[-500:]
    except subprocess.TimeoutExpired:
        return False, "timeout"
    finally:
        _os.unlink(path)


def run_humaneval(humaneval, runs, loaded, limit=20):
    problems = humaneval[:limit] if limit > 0 else humaneval
    print(f"{len(problems)} HumanEval problems; runs: {list(loaded.keys())}")
    humaneval_results = {}
    for model_name, mode in runs:
        key = (model_name, mode)
        if model_name not in loaded:
            print(f"\n=== humaneval {model_name}/{mode} === skipped (model not loaded above)")
            continue
        generate = loaded[model_name]
        print(f"\n=== humaneval {model_name}/{mode} ===")
        rows = []
        started = time.time()
        for i, problem in enumerate(problems, 1):
            try:
                comp = generate(
                    problem["prompt"], mode, HUMANEVAL_MAX_NEW_TOKENS, HE_CHAT_INSTRUCTION
                )
                program = build_program(problem, mode, comp["text"])
                passed, err = run_program(program)
                row = {
                    "task_id": problem["task_id"],
                    "passed": passed,
                    "error": None if passed else err,
                    "tok_in": comp["tok_in"],
                    "tok_out": comp["tok_out"],
                    "latency_ms": comp["latency_ms"],
                }
            except Exception as e:
                row = {
                    "task_id": problem["task_id"],
                    "passed": False,
                    "error": repr(e),
                    "tok_in": None,
                    "tok_out": None,
                    "latency_ms": None,
                }
            rows.append(row)
            if i % 25 == 0 or i == len(problems):
                print(f"  {i}/{len(problems)} done ({time.time() - started:.0f}s elapsed)")
        humaneval_results[key] = rows
    return humaneval_results


def report_humaneval(humaneval_results):
    print(f"{'model':<10} {'mode':<6} {'n':>5} {'pass@1':>8}")
    print("-" * 32)
    humaneval_pass_at_1 = {}
    for key, rows in humaneval_results.items():
        n = len(rows)
        passed = sum(r["passed"] for r in rows)
        rate = passed / n if n else None
        humaneval_pass_at_1[key] = rate
        model_name, mode = key
        print(f"{model_name:<10} {mode:<6} {n:>5} {pct(rate):>8}")
    return humaneval_pass_at_1
