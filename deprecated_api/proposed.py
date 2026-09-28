"""Two bounded chat verifiers sharing one mapping-based implementation.

Generation-time knowledge comes exclusively from mappings.json. The generation
core receives only input/alias/reference/library metadata; gold evaluation
fields are used afterwards by the unchanged annotation.label function.
"""

from .annotation import label, postprocess
from .runner import METHODS


class APIKnowledgeBase:
    """Actual mappings schema: list of {lib, deprecated, replacement} strings.

    'active' means a known replacement target, not a claim about every library
    release. The dataset contains no version information.
    """

    def __init__(self, mappings):
        self.deprecated = {}
        self.active = set()
        for row in mappings:
            library, old, new = row["lib"], row["deprecated"], row["replacement"]
            key = (library, old)
            if key in self.deprecated and self.deprecated[key] != new:
                raise ValueError(f"Conflicting replacements for {key}")
            self.deprecated[key] = new
            self.active.add((library, new))

    def check_api(self, api_name, library, target_version=None):
        if target_version is not None:
            raise ValueError("mappings.json has no version fields; target_version is unsupported")
        key = (library, api_name)
        replacement = self.deprecated.get(key)
        status = (
            "deprecated"
            if replacement is not None
            else ("active" if key in self.active else "unknown")
        )
        return {"api": api_name, "library": library, "status": status, "replacement": replacement}


_knowledge = None


def configure_verifier(mappings):
    """Initialize once per notebook from the independently loaded mappings file."""
    global _knowledge
    _knowledge = APIKnowledgeBase(mappings)
    return _knowledge


def check_api(api_name, library, target_version=None):
    if _knowledge is None:
        raise RuntimeError("Call configure_verifier(mappings) before using the verifier")
    return _knowledge.check_api(api_name, library, target_version)


def repair_feedback(issues):
    lines = ["The generated completion uses deprecated API(s):", ""]
    for issue in sorted(issues, key=lambda issue: issue["api"]):
        lines.extend([f"- {issue['api']}", f"  replacement: {issue['replacement']}"])
    lines.extend(
        [
            "",
            "Rewrite the completion using the replacement API(s).",
            "Preserve the intended behavior.",
            "Return only the repaired Python completion/code with no explanation.",
        ]
    )
    return "\n".join(lines)


def verify_and_repair(context, generate, mode, max_repairs):
    """Generation-only core. ``context`` has no evaluation gold fields."""
    if mode != "chat":
        raise ValueError("Proposed verifier methods support chat mode only")
    if max_repairs not in (1, 2):
        raise ValueError("Only one or two repair rounds are supported")
    if _knowledge is None:
        raise RuntimeError("Call configure_verifier(mappings) before generation")

    calls, trace = [], []
    feedback = None
    comp = generate(context["probing input"], mode)
    for round_number in range(max_repairs + 1):
        calls.append(comp)
        completion, apis = postprocess(context, comp["text"], mode)
        apis = sorted(apis)
        checks = [check_api(api, context["lib"]) for api in apis]
        issues = [check for check in checks if check["status"] == "deprecated"]
        trace.append(
            {
                "round": round_number,
                "completion": completion,
                "apis": apis,
                "checks": checks,
                "issues": issues,
                "feedback": feedback,
                "raw": comp["text"],
                "finish_reason": comp["finish_reason"],
                **{
                    field: comp[field] for field in ("tok_in", "tok_out", "tok_think", "latency_ms")
                },
            }
        )
        if not issues or round_number == max_repairs:
            break
        feedback = repair_feedback(issues)
        prompt = (
            f"Original code prompt:\n{context['probing input']}\n\n"
            f"Generated completion:\n{completion}\n\n{feedback}"
        )
        # Same chat backend and token budget. Identity instruction avoids wrapping
        # repair feedback in the baseline's 'complete the next line' instruction.
        # Only {code} is formatted, so braces in generated Python are safe.
        comp = generate(prompt, mode, instruction="{code}")

    totals = {}
    for field in ("tok_in", "tok_out", "tok_think", "latency_ms"):
        values = [call[field] for call in calls]
        # Unknown usage stays unknown rather than reporting a partial sum as total.
        totals[field] = sum(values) if all(value is not None for value in values) else None
    return {
        "completion": completion,
        "apis": apis,
        "raw": comp["text"],
        "finish_reason": comp["finish_reason"],
        **totals,
        "num_calls": len(calls),
        "repair_rounds": len(calls) - 1,
        "initial_completion": trace[0]["completion"],
        "final_completion": completion,
        "initial_apis": trace[0]["apis"],
        "final_apis": apis,
        "issues": trace[0]["issues"],
        "final_issues": issues,
        "trace": trace,
    }


def _method(sample, generate, mode, max_repairs):
    # Deliberate allowlist: do not pass function/reference/gold answer fields to
    # generation, prompts, feedback, or API checking.
    context = {key: sample[key] for key in ("probing input", "reference dict", "alias dict", "lib")}
    result = verify_and_repair(context, generate, mode, max_repairs)
    # Evaluation boundary: only now consult the original benchmark's gold labels.
    result["label"] = label(sample, result["apis"])
    return result


def verifier_one_shot_method(sample, generate, mode):
    return _method(sample, generate, mode, max_repairs=1)


def verifier_iterative_method(sample, generate, mode):
    return _method(sample, generate, mode, max_repairs=2)


verifier_one_shot_method.supported_modes = ("chat",)
verifier_iterative_method.supported_modes = ("chat",)
METHODS["verifier_one_shot"] = verifier_one_shot_method
METHODS["verifier_iterative"] = verifier_iterative_method
