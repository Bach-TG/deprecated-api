# Deprecated-API benchmark pipeline

Minimal Wang et al. benchmark reproduction plus the project's two proposed
mapping-based verifiers. The refactoring source supplied in this checkout was
`notebooks/share-deapi.ipynb`; `00_deprecated-api.ipynb` was only a starter.
The original monolith is retained for provenance, with its embedded Gemini key
removed. The two DeepSeek baseline modes and two proposed methods can each run as
separate Kaggle jobs to fit session limits; Stage 02 combines their outputs.

```text
                    ┌──► 00_baseline (choose raw/chat) ──┐
benchmark JSON ─────┤                                    ├──► 02_evaluate
                    └──► 01_proposed_methods (choose one-shot/iterative) ─┘
```

The single baseline notebook runs one selected mode per session. Run it once as
raw and once as chat, using separate Kaggle kernel refs; each run writes a distinct
artifact directory with the same `run_config.json`. The proposed-method notebook
also runs one selected method per session under distinct refs/artifact directories.
Stage 02 reads all four output sources and rejects mismatched configs.
Every Kaggle push
bundles the **current** `deprecated_api/` package using nbflow. Upstream outputs
provide artifacts, not importable source code.

## Setup

```bash
uv sync --group dev
uv run python -m ipykernel install --user \
  --name deprecated_api \
  --display-name "Python (deprecated-api)"
```

For real model runs on a GPU server, install the optional model dependencies:

```bash
uv sync --group dev --extra experiments
```

Kaggle uses its existing CUDA PyTorch and installs the original notebook's
`transformers accelerate google-genai` dependencies in the generation stages.
For Gemini, provide `GEMINI_API_KEY` in the process environment, or attach a Kaggle
secret named `GEMINI_API_KEY` to each stage using it. No key is written to config.
`GEMINI_MODEL` can override the default `gemini-3.1-flash-lite`, which uses
`thinking_level="minimal"`. Every generation job uses the same configured model
settings. Missing Gemini credentials skip that backend, as in the original runner.

Put these immutable benchmark files in `data/raw/` locally, or at the root of an
attached Kaggle dataset:

- `mappings.json` (145 records: `lib`, `deprecated`, `replacement`)
- `sample.json` (~2,101 prompts)
- `smoke.json` (32 prompts)
- `humaneval.json` (164 control problems)
- `sample_full.json` (~27,427 prompts), required only for `full`

## Notebook editing and the single split setting

Canonical notebooks are committed under `notebooks/`. Editable Jupytext files,
local execution results, and Kaggle metadata are generated under `.notebook/`.


```bash
notebook edit notebooks/00_baseline.ipynb
notebook sync-current .notebook/notebooks__00_baseline/00_baseline.ju.py
```

On a fresh checkout, use `notebook pull notebooks/<stage>.ipynb` to create each
hidden text mirror. Never edit `.ipynb` JSON directly. See
`NOTEBOOK_README.md` and `AI_DATA_SCIENCE_WORKFLOW_README.md` for the global workflow.

Both generation notebooks read their split from the shared project setting:
`deprecated_api.pipeline.DEFAULT_SPLIT`. The value in this working copy is
`full`; use `DEPAPI_SPLIT=sample` for Kaggle's ~2,101-prompt split, or `smoke` for
development. To change the source default, edit that one project setting and push
the updated package with both generation notebooks.

```python
DEFAULT_SPLIT = os.environ.get("DEPAPI_SPLIT", "full")
LIMIT = 0
SAMPLE_SEED = 42
```

The `DEFAULT_SPLIT` value controls all generation jobs. Set it before running
raw, chat, one-shot, and iterative jobs. Each constructs its own config; Stage 02 verifies
all configs match. Keep `LIMIT=0`, `SAMPLE_SEED=42`, model/run settings and generation
budget the same across those jobs. `LIMIT` retains its
original meaning: a cap **per (library, category)** after seeded shuffling, not a
total prompt cap.

`notebooks/00_baseline.ipynb` has a `BASELINE_MODE` setting (`raw` or `chat`).
`notebooks/01_proposed_methods.ipynb` has a `PROPOSED_MODE` setting (`verifier_one_shot`
or `verifier_iterative`). `DEFAULT_RUNS` records both baseline modes; proposed methods use the chat run.
DeepSeek remains
`deepseek-ai/deepseek-coder-1.3b-instruct`, greedy, 50 new tokens.

## Artifact layout and resume

Output root is `/kaggle/working` on Kaggle and the project root locally/server,
using the existing artifact/config helpers. A durable alternative root can be
set with the existing `NBFLOW_PROJECT_ROOT` environment variable on a server.

```text
artifacts/
├── 00_baseline_raw/
│   ├── run_config.json
│   ├── manifest.json
│   └── results/baseline/results_deepseek_raw.jsonl
├── 00_baseline_chat/
│   ├── run_config.json
│   ├── manifest.json
│   └── results/baseline/results_deepseek_chat.jsonl
├── 01_verifier_one_shot/
│   ├── run_config.json
│   ├── manifest.json
│   └── results/verifier_one_shot/results_<model>_chat.jsonl
├── 01_verifier_iterative/
│   ├── run_config.json
│   ├── manifest.json
│   └── results/verifier_iterative/results_<model>_chat.jsonl
└── 02_evaluate/
    ├── run_config.json
    ├── manifest.json
    ├── comparison.json
    ├── cost.json
    └── humaneval.json                 # when explicitly enabled
reports/figures/02_evaluate/comparison.png
```

Manifest file paths are relative to their stage directory. Result rows are
appended and flushed immediately; completed sample IDs are skipped on rerun.
As before, this includes `Error` rows. Rerun against the same data and config.
Changing configurations in a populated stage directory fails clearly: archive
the previous run's artifacts before switching smoke/sample/full or model settings.
The evaluator can display partial runs with their actual row/error counts.

On Kaggle, `/kaggle/working` survives in saved notebook outputs, not across arbitrary
new sessions. To resume a fresh session, restore that stage's saved artifact
directory into `/kaggle/working/artifacts/<stage>/` before running it. Attaching an
upstream notebook alone does not make its read-only files writable checkpoints.

## Kaggle: initialize and run the split baseline

Replace `OWNER`, `PROJECT`, and `BENCHMARK` with your Kaggle owner, slug prefix,
and benchmark dataset reference. The dataset must contain the four required JSON
files. No generated Kaggle mount names are used in code; the project input helper
searches nested layouts such as `/kaggle/input/datasets/<owner>/<slug>/` too.

```bash
OWNER=your-kaggle-owner
PROJECT=deprecated-api
BENCHMARK=dataset-owner/benchmark-dataset
```

Attach the benchmark dataset explicitly to each run. First make the baseline
config cell resolve `BASELINE_MODE` to `raw` (the default), then initialize and
run the raw job:

```bash
notebook kaggle-init notebooks/00_baseline.ipynb \
  --ref "$OWNER/$PROJECT-00-baseline-raw" \
  --dataset "$BENCHMARK" --gpu NvidiaTeslaT4 --internet
notebook kaggle-push notebooks/00_baseline.ipynb
notebook kaggle-status notebooks/00_baseline.ipynb
```

After raw completes, change the config cell's fallback from `"raw"` to `"chat"`
(or set `DEPAPI_BASELINE_MODE=chat`), sync it, and push chat under a
**different kernel ref**:

```bash
notebook sync-current .notebook/notebooks__00_baseline/00_baseline.ju.py
notebook kaggle-init notebooks/00_baseline.ipynb \
  --ref "$OWNER/$PROJECT-00-baseline-chat" \
  --dataset "$BENCHMARK" --gpu NvidiaTeslaT4 --internet
notebook kaggle-push notebooks/00_baseline.ipynb
notebook kaggle-status notebooks/00_baseline.ipynb
```

The two refs keep their outputs independently attachable even though both came
from `notebooks/00_baseline.ipynb`. Attach the benchmark dataset to each run.
Run one-shot from the proposed notebook's default config:

```bash
notebook kaggle-init notebooks/01_proposed_methods.ipynb \
  --ref "$OWNER/$PROJECT-01-verifier-one-shot" \
  --dataset "$BENCHMARK" --gpu NvidiaTeslaT4 --internet
notebook kaggle-push notebooks/01_proposed_methods.ipynb
notebook kaggle-status notebooks/01_proposed_methods.ipynb
```

After it succeeds, change the `PROPOSED_MODE` fallback to `"verifier_iterative"`,
sync, and push the second mode under another ref:

```bash
notebook sync-current .notebook/notebooks__01_proposed_methods/01_proposed_methods.ju.py
notebook kaggle-init notebooks/01_proposed_methods.ipynb \
  --ref "$OWNER/$PROJECT-01-verifier-iterative" \
  --dataset "$BENCHMARK" --gpu NvidiaTeslaT4 --internet
notebook kaggle-push notebooks/01_proposed_methods.ipynb
notebook kaggle-status notebooks/01_proposed_methods.ipynb
```

After raw, chat, one-shot, and iterative all succeed, attach their four refs to
evaluation:

```bash
notebook kaggle-init notebooks/02_evaluate.ipynb \
  --ref "$OWNER/$PROJECT-02-evaluate" \
  --dataset "$BENCHMARK" \
  --kernel "$OWNER/$PROJECT-00-baseline-raw" \
  --kernel "$OWNER/$PROJECT-00-baseline-chat" \
  --kernel "$OWNER/$PROJECT-01-verifier-one-shot" \
  --kernel "$OWNER/$PROJECT-01-verifier-iterative"
notebook kaggle-push notebooks/02_evaluate.ipynb
notebook kaggle-status notebooks/02_evaluate.ipynb
notebook kaggle-output notebooks/02_evaluate.ipynb
```

After editing a hidden mirror, the equivalent push is:
`notebook kaggle-push-current .notebook/notebooks__<stage>/<stage>.ju.py`.
The four generation jobs need no upstream notebook sources. Stage 02 needs all
four kernel sources; benchmark inputs are not assumed transitive. Its config check
explains mismatches.

## Server: run the full chain with the same code

1. Install the experiment extra and register the kernel using Setup above.
2. Place all five JSON files, including `sample_full.json`, in `data/raw/`.
3. Use a clean durable output root (or archive an earlier sample/smoke run).
4. Optionally export Gemini credentials/model selection in your shell.
5. Run from the project root:

```bash
notebook pull notebooks/00_baseline.ipynb
notebook pull notebooks/01_proposed_methods.ipynb
notebook pull notebooks/02_evaluate.ipynb

# nbflow delegates execution to nbconvert. Disable its short default cell
# timeout for hours-long experiment cells, using local-only notebook config.
mkdir -p .notebook/jupyter
cat > .notebook/jupyter/jupyter_nbconvert_config.py <<'PY'
c = get_config()
c.ExecutePreprocessor.timeout = -1
PY
export JUPYTER_CONFIG_DIR="$PWD/.notebook/jupyter"

export DEPAPI_SPLIT=full
export DEPAPI_BASELINE_MODE=raw
notebook run-current .notebook/notebooks__00_baseline/00_baseline.ju.py
export DEPAPI_BASELINE_MODE=chat
notebook run-current .notebook/notebooks__00_baseline/00_baseline.ju.py
export DEPAPI_PROPOSED_MODE=verifier_one_shot
notebook run-current .notebook/notebooks__01_proposed_methods/01_proposed_methods.ju.py
export DEPAPI_PROPOSED_MODE=verifier_iterative
notebook run-current .notebook/notebooks__01_proposed_methods/01_proposed_methods.ju.py
notebook run-current .notebook/notebooks__02_evaluate/02_evaluate.ju.py
```

The raw/chat and one-shot/iterative executions read the same `DEFAULT_SPLIT` and
write separate artifact stages. Stage 02 reads the raw baseline config to load the
dataset and verifies all configs match. Rerun an interrupted job with the same mode
to resume. For a cheap real-model development
run, use `DEPAPI_SPLIT=smoke`.
For a local sample run, use `DEPAPI_SPLIT=sample` instead of `full`.

## Shared implementation and scientific boundaries

| Module | Responsibility |
| --- | --- |
| `deprecated_api/dataset.py` | Required-file loading, split selection, original seeded cap |
| `deprecated_api/annotation.py` | `extract_first_func`, `clean_pred`, `extract_first_statement`, `extract_apis_in_first_stmt`, `strip_fences`, `postprocess`, `label` |
| `deprecated_api/backends.py` | Original DeepSeek/Gemini loaders, generation, caching, retry/pacing |
| `deprecated_api/runner.py` | `baseline_method(sample, generate, mode)`, registry, append/flush/ID resume |
| `deprecated_api/proposed.py` | Mapping KB, `check_api`, deterministic feedback, shared bounded repair loop |
| `deprecated_api/evaluation.py` | Existing AUP/DUR, Table III, library/cost/comparison/plot/insight logic |
| `deprecated_api/humaneval.py` | Original model/mode HumanEval control |
| `deprecated_api/pipeline.py` | Small config/manifests/upstream-file orchestration helpers |

### Proposed methods

- `verifier_one_shot`: initial generation, check, zero or one repair.
- `verifier_iterative`: initial generation, check, zero to two repairs, rechecking
  after each. Both use the same implementation and independent initial drafts.
- **Chat only.** Baseline retains DeepSeek/raw for the Table III gate; compare
  methods on matching DeepSeek/chat or Gemini/chat. No fabricated raw verifier runs.
- The knowledge base uses only `mappings.json`'s actual fields. No versions are
  supplied: `target_version` queries are explicitly unsupported. `active` means
  listed replacement target; unlisted calls remain `unknown`. Deprecation wins
  if an API is both a source and a target. Checking is scoped to the sample library
  (`pytorch` is the dataset's library name for `torch.*` calls).
- Only prompt, library, alias and reference dictionaries reach the generation
  core. Gold `deprecated api`/`replacement api` fields are consulted only by the
  unchanged evaluator after generation. Full `function`/gold `reference` text is
  never put in repair prompts.
- API extraction remains the original first-statement heuristic, with its existing
  alias/reference normalization. Later statements, changed imports/aliases,
  non-call properties, and complex data flow can be missed. Unknown calls do not
  trigger repairs. A passing check is not a semantic-correctness guarantee.
- Every deprecated API found in that statement is listed in deterministic feedback.
  Repairs preserve backend/token settings but use an explicit repair instruction.
  Completion, raw output and finish reason describe the final generation; tokens
  and generation latency sum all calls (unknown usage remains `None`).
  `num_calls`, initial/final completions/APIs/issues and per-round traces are saved.

### Evaluator and HumanEval

AUP/DUR formulas, Error exclusion, outdated/`up-to-dated` groups, library breakdown,
Table III targets and 3-point tolerance are unchanged. Table III still runs only
against baseline/DeepSeek/raw and is not meaningful on the 32-prompt smoke split.
For reproduction deviations, inspect per-library counts, AUP and DUR alongside
the aggregate gate before drawing conclusions; no automatic scientific correction
is made. The original comparison section's missing `glob` import and hard-coded
`output/` path were replaced by explicit stage-result loading.

Existing limitations retained: the cost table's `calls` is a row count, not the
new `num_calls`; latency excludes pacing and failed retry attempts just as before;
Error IDs are not automatically retried; malformed/truncated JSONL is not silently
recovered. The original insights rank aggregate DUR without a new error-analysis
or statistical-testing framework.

HumanEval is isolated and optional (`RUN_HUMANEVAL=True` in Stage 02). It evaluates
**model/mode behavior, not baseline-versus-verifier intervention**. Its prompt,
384-token budget, subprocess timeout, pass@1 logic, and chat full-function/signature
limitation are preserved. Enabling it on Kaggle also requires internet and the
model credentials/configuration for Stage 02; reinitialize with those options and
all four kernel sources.

Only the two proposed verifiers are implemented. ReplaceAPI, InsertPrompt, model
editing, CURE, RAG, web-document retrieval, new metrics and statistical tests are
outside this prototype.


## Quality checks

```bash
uv run ruff check .
uv run pytest
```

The tests use scripted generators, including an end-to-end execution of the three
canonical notebooks (with raw/chat baseline and one-shot/iterative configs) on the
**real smoke split**, in fresh namespaces
and temporary output directories. They verify comparison membership, bounded
repairs, gold-label independence, usage totals and checkpoint resume. No model
download/API calls or sample/full experiments are performed. Dataset-dependent
tests skip when the locally supplied JSON files are absent. This validates pipeline
wiring, not real-model quality or a successful Wang reproduction.

During this refactor, the stages were also run sequentially through
`notebook run-current` with a local-only scripted backend. Those execution copies
and synthetic artifacts are under `.notebook/` (the artifacts specifically under
`.notebook/offline-smoke/`), separate from real experiment outputs. An executable-AST
audit confirmed the moved annotation, baseline, generation, summary and HumanEval
helper functions match the supplied monolith. All three dataset splits were loaded
to validate their counts; no sample/full inference was run.
