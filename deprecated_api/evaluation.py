"""Wang benchmark reports moved from the monolithic notebook.

Formulas, denominators, Table III targets/tolerance, cost row counts, and
insights intentionally retain the original implementation's semantics.
"""

import matplotlib.pyplot as plt


def summarize(rows):
    def block(rs):
        n = len(rs)
        plausible = [r for r in rs if r["label"] in ("DepC", "RepC")]
        dep = [r for r in plausible if r["label"] == "DepC"]
        return {
            "n": n,
            "AUP": (len(plausible) / n) if n else None,
            "DUR": (len(dep) / len(plausible)) if plausible else None,
        }

    ok = [r for r in rows if r["label"] != "Error"]
    errs = [r for r in rows if r["label"] == "Error"]
    by_lib = {
        lib: block([r for r in ok if r["lib"] == lib]) for lib in sorted({r["lib"] for r in ok})
    }
    return {
        "n": len(rows),
        "errors": len(errs),
        "errors_O": sum(1 for r in errs if r["category"] == "outdated"),
        "errors_U": sum(1 for r in errs if r["category"] == "up-to-dated"),
        "O": block([r for r in ok if r["category"] == "outdated"]),
        "U": block([r for r in ok if r["category"] == "up-to-dated"]),
        "All": block(ok),
        "by_lib": by_lib,
    }


def pct(x):
    return "-" if x is None else f"{100 * x:.1f}%"


def comparison_table(summaries):
    header = (
        f"{'method':<12} {'model':<10} {'mode':<6} {'n':>5} {'err':>4} "
        f"{'AUP(O)':>7} {'AUP(U)':>7} {'AUP(All)':>9} "
        f"{'DUR(O)':>7} {'DUR(U)':>7} {'DUR(All)':>9}"
    )
    print(header)
    print("-" * len(header))
    for (method_name, model_name, mode), s in summaries.items():
        print(
            f"{method_name:<12} {model_name:<10} {mode:<6} {s['n']:>5} {s['errors']:>4} "
            f"{pct(s['O']['AUP']):>7} {pct(s['U']['AUP']):>7} {pct(s['All']['AUP']):>9} "
            f"{pct(s['O']['DUR']):>7} {pct(s['U']['DUR']):>7} {pct(s['All']['DUR']):>9}"
        )


TABLE_III = {
    "AUP_O": 9.2,
    "AUP_U": 11.8,
    "AUP_All": 11.0,
    "DUR_O": 69.7,
    "DUR_U": 11.6,
    "DUR_All": 27.2,
}
TOL = 3.0


def table_iii_gate(summaries):
    key = ("baseline", "deepseek", "raw")
    if key not in summaries:
        print(f"{key} not in this run's RUNS/METHODS/results -- nothing to gate")
        return None
    s = summaries[key]
    got = {
        "AUP_O": 100 * (s["O"]["AUP"] or 0),
        "AUP_U": 100 * (s["U"]["AUP"] or 0),
        "AUP_All": 100 * (s["All"]["AUP"] or 0),
        "DUR_O": 100 * (s["O"]["DUR"] or 0),
        "DUR_U": 100 * (s["U"]["DUR"] or 0),
        "DUR_All": 100 * (s["All"]["DUR"] or 0),
    }
    all_pass = True
    for k, want in TABLE_III.items():
        d = abs(got[k] - want)
        ok = d <= TOL
        all_pass &= ok
        print(f"{'PASS' if ok else 'FAIL'}  {k:8s} got={got[k]:.1f} want={want} delta={d:.1f}")
    print(
        "\n"
        + (
            "ALL WITHIN TOLERANCE"
            if all_pass
            else "OUT OF TOLERANCE -- see README/spec for the per-library deviation-hunting steps"
        )
    )
    return {"got": got, "all_pass": all_pass}


def per_library(summaries):
    libs = sorted({lib for s in summaries.values() for lib in s["by_lib"]})
    for (method_name, model_name, mode), s in summaries.items():
        print(f"\n=== {method_name}/{model_name}/{mode} by library ===")
        header = f"{'lib':<14} {'n':>5} {'AUP':>7} {'DUR':>7}"
        print(header)
        print("-" * len(header))
        for lib in libs:
            b = s["by_lib"].get(lib, {"n": 0, "AUP": None, "DUR": None})
            print(f"{lib:<14} {b['n']:>5} {pct(b['AUP']):>7} {pct(b['DUR']):>7}")


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def fmt(x, nd=0):
    return "-" if x is None else f"{x:.{nd}f}"


def cost_table(all_results, runs):
    baseline_key = ("baseline",) + tuple(runs[0])
    cost = {}
    for key, rows in all_results.items():
        cost[key] = {
            "calls": len(rows),
            "tok_in": mean([r.get("tok_in") for r in rows]),
            "tok_out": mean([r.get("tok_out") for r in rows]),
            "latency_ms": mean([r.get("latency_ms") for r in rows]),
        }
    base = cost.get(baseline_key)
    print(f"baseline: {baseline_key}\n")
    header = (
        f"{'method':<12} {'model':<10} {'mode':<6} {'calls':>6} "
        f"{'tok_in':>7} {'tok_out':>7} {'lat_ms':>8} {'vs base':>8}"
    )
    print(header)
    print("-" * len(header))
    for key, c in cost.items():
        ratio = "-"
        if base and base["latency_ms"] and c["latency_ms"] is not None:
            ratio = f"{c['latency_ms'] / base['latency_ms']:.2f}x"
        method_name, model_name, mode = key
        print(
            f"{method_name:<12} {model_name:<10} {mode:<6} {c['calls']:>6} "
            f"{fmt(c['tok_in'], 1):>7} {fmt(c['tok_out'], 1):>7} "
            f"{fmt(c['latency_ms'], 0):>8} {ratio:>8}"
        )
    return cost


def plot_comparison(disk_summaries, output_path=None):
    if disk_summaries:
        configs = list(disk_summaries.keys())
        labels = [f"{me}\n{m}/{mo}" for me, m, mo in configs]
        aup_vals = [(disk_summaries[k]["All"]["AUP"] or 0) * 100 for k in configs]
        dur_vals = [(disk_summaries[k]["All"]["DUR"] or 0) * 100 for k in configs]
        x = range(len(configs))
        width = 0.35
        fig, ax = plt.subplots(figsize=(max(6, len(configs) * 1.6), 4))
        ax.bar([i - width / 2 for i in x], aup_vals, width, label="AUP")
        ax.bar([i + width / 2 for i in x], dur_vals, width, label="DUR")
        ax.set_xticks(list(x))
        ax.set_xticklabels(labels, fontsize=8)
        ax.set_ylabel("%")
        ax.set_title("AUP vs DUR by (method, model, mode)")
        ax.legend()
        plt.tight_layout()
        if output_path is not None:
            fig.savefig(output_path)
        plt.show()
        return fig
    return None


def insights(disk_summaries):
    if disk_summaries:
        print("=== Insights ===")
        by_dur = sorted(
            (
                (k, s["All"]["DUR"])
                for k, s in disk_summaries.items()
                if s["All"]["DUR"] is not None
            ),
            key=lambda kv: kv[1],
        )
        if by_dur:
            best, worst = by_dur[0], by_dur[-1]
            print(f"Lowest DUR (best):  {best[0]} at {pct(best[1])}")
            print(f"Highest DUR (worst): {worst[0]} at {pct(worst[1])}")
        by_aup = sorted(
            (
                (k, s["All"]["AUP"])
                for k, s in disk_summaries.items()
                if s["All"]["AUP"] is not None
            ),
            key=lambda kv: kv[1],
            reverse=True,
        )
        if by_aup:
            print(f"Highest AUP: {by_aup[0][0]} at {pct(by_aup[0][1])}")
        for (method_name, model_name, mode), s in disk_summaries.items():
            if method_name == "baseline":
                continue
            base_key = ("baseline", model_name, mode)
            if base_key not in disk_summaries:
                continue
            base_s = disk_summaries[base_key]
            if s["All"]["DUR"] is not None and base_s["All"]["DUR"] is not None:
                delta = (base_s["All"]["DUR"] - s["All"]["DUR"]) * 100
                direction = "reduces" if delta > 0 else "increases"
                print(
                    f"{method_name} vs baseline ({model_name}/{mode}): DUR {direction} by "
                    f"{abs(delta):.1f} points ({pct(s['All']['DUR'])} "
                    f"vs {pct(base_s['All']['DUR'])})"
                )
    else:
        print("nothing to compare yet.")
