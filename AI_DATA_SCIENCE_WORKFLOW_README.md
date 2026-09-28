# Personal AI/Data Science Project Workflow

> A lightweight, reproducible workflow for AI/Data Science projects using:
>
> - a **Cookiecutter Data Science–style structure**
> - **uv** for Python environments and dependencies
> - **nbflow** for Jupyter notebook editing/sync/execution/Kaggle
> - **OpenCode + Neovim** for notebook editing through Jupytext text files
> - **Git + optional GitHub**
> - **Kaggle notebooks chained through notebook outputs**
>
> The main goal is simple:
>
> **run one project setup command, start working immediately, and only add project-specific infrastructure when it is actually needed.**

---

## 1. Core design

The workflow separates a project into three kinds of state:

| Kind | Source of truth | Purpose |
|---|---|---|
| Reusable code | project Python package | data/model/metrics/features/helpers |
| Notebook | `notebooks/**/*.ipynb` | committed/shareable notebook + outputs |
| Local notebook editing state | `.notebook/**` | `.ju.py`, metadata, local runs, Kaggle staging |
| Environment | `pyproject.toml` + `uv.lock` | dependencies and reproducibility |
| Kaggle pipeline data | upstream notebook outputs | artifacts passed between notebook stages |

The most important rule is:

> **Notebooks orchestrate and explain. Reusable logic lives in Python files.**

This gives the convenience of notebooks without turning the project into a collection of duplicated, stateful notebook code.

---

# 2. Global tooling

The workflow has two main global tools.

## `ai-project`

Personal project bootstrap command.

Typical usage:

```bash
ai-project my-project
```

It creates a lightweight CCDS-style project, initializes Git, creates a Python environment with `uv`, creates the first notebook, and registers it with nbflow.

Optional GitHub creation:

```bash
ai-project my-project --github
```

Optional Kaggle initialization:

```bash
ai-project my-project \
  --kaggle-ref bachgia2604/my-project
```

The script is installed at:

```text
~/.local/bin/ai-project
```

---

## `nbflow`

Notebook workflow engine.

Main implementation:

```text
~/.local/share/nbflow/nbflow.py
```

The shell command is:

```bash
notebook ...
```

nbflow manages:

- `.ipynb ↔ .ju.py`
- Jupytext synchronization
- local execution
- notebook metadata
- Kaggle metadata
- Kaggle push/status/output
- bundling project `.py` code into Kaggle notebooks

Its own isolated Python environment lives under:

```text
~/.local/share/nbflow/venv/
```

and provides tools such as:

```text
jupytext
jupyter
kaggle
```

---

# 3. Global OpenCode instructions

Global notebook behavior is defined in:

```text
~/.config/opencode/AGENTS.md
```

Current rules:

```markdown
# Personal notebook workflow

When working with Jupyter notebooks:

- Canonical, committed notebooks live under `notebooks/**/*.ipynb`.
- Do not edit `.ipynb` JSON directly unless explicitly requested.
- Prefer editing the corresponding local hidden text notebook:
  `.notebook/**/<name>.ju.py`
- Hidden notebooks use Jupytext/Neopyter percent-style `# %%` cell markers.
- Preserve cell boundaries unless restructuring is explicitly requested.
- After editing a `.ju.py` notebook, synchronize it with:
  `notebook sync-current <path-to-.ju.py>`
- To execute the current hidden notebook locally, use:
  `notebook run-current <path-to-.ju.py>`
- Initialize Kaggle once using the canonical notebook:
  `notebook kaggle-init notebooks/<name>.ipynb --ref <owner>/<slug>`
- After editing a hidden `.ju.py`, push it to Kaggle with:
  `notebook kaggle-push-current <path-to-.ju.py>`
- From the project root, this equivalent canonical-notebook command is also valid:
  `notebook kaggle-push notebooks/<name>.ipynb`
- After a canonical `.ipynb` changes externally, regenerate the hidden text notebook:
  `notebook pull notebooks/<name>.ipynb`
- Keep all nbflow-generated files, execution artifacts, and Kaggle metadata under
  `.notebook/`.
```

This applies to every project.

Each project also gets its own `AGENTS.md` describing project-specific structure and boundaries.

---

# 4. Default project structure

A new project created by:

```bash
ai-project my-project
```

uses this structure:

```text
my-project/
├── .notebook/                    # local-only nbflow workspace
│
├── data/
│   ├── external/
│   ├── interim/
│   ├── processed/
│   └── raw/
│
├── models/
│
├── notebooks/
│   └── 00_my-project.ipynb
│
├── references/
│
├── reports/
│   └── figures/
│
├── my_project/
│   ├── modeling/
│   │   ├── __init__.py
│   │   ├── evaluate.py
│   │   ├── predict.py
│   │   └── train.py
│   │
│   ├── __init__.py
│   ├── artifacts.py
│   ├── config.py
│   ├── dataset.py
│   ├── features.py
│   └── plots.py
│
├── tests/
│   └── test_import.py
│
├── .gitignore
├── .python-version
├── AGENTS.md
├── pyproject.toml
├── README.md
└── uv.lock
```

This intentionally keeps the project small.

The following are **not** added by default:

```text
Docker
DVC
MLflow
Hydra
FastAPI
Dagster
Prefect
configs/
docs/
infra/
CI/CD
```

Add them only when the project actually needs them.

---

# 5. CCDS philosophy used by this setup

The structure follows the useful core ideas of Cookiecutter Data Science:

```text
data/raw
data/interim
data/processed
data/external

models/
notebooks/
references/
reports/
```

The important meanings are:

### `data/raw/`

Original immutable data.

Do not manually overwrite transformed data here.

### `data/interim/`

Intermediate transformations.

### `data/processed/`

Final local datasets ready for modeling or analysis.

### `data/external/`

Data originating outside the main project dataset.

### `models/`

Local model artifacts.

### `notebooks/`

Canonical notebooks that are committed/shared.

### `references/`

Papers, schemas, documentation, data dictionaries, etc.

### `reports/figures/`

Generated analysis/report figures.

---

# 6. Python package: reusable project code

Reusable code belongs in:

```text
my_project/
```

For example:

```text
my_project/
├── dataset.py
├── features.py
├── artifacts.py
├── plots.py
└── modeling/
    ├── train.py
    ├── predict.py
    └── evaluate.py
```

A notebook should preferably look like:

```python
from my_project.dataset import prepare_dataset
from my_project.modeling.train import train_model
from my_project.modeling.evaluate import evaluate_model
```

rather than containing hundreds of lines of reusable implementation.

---

## What stays in notebooks?

Good notebook content:

- research questions
- experiment orchestration
- ad-hoc exploration
- markdown explanation
- visualization
- result inspection
- error analysis
- conclusions
- calls into reusable project functions

Example:

```python
from my_project.modeling.train import train_model

run = train_model(config)
run.metrics
```

---

## What moves to Python files?

Move code into the package when it is:

- reused in multiple notebooks
- a model class
- a loss function
- preprocessing logic
- data loading logic
- feature engineering
- evaluation metrics
- checkpoint logic
- inference logic
- reusable plotting logic
- important enough to test

A useful heuristic:

> If copying the cell to another notebook feels reasonable, it probably belongs in `.py`.

---

# 7. Python environment with `uv`

Each project uses:

```text
pyproject.toml
uv.lock
.venv/
```

Default runtime dependencies:

```text
numpy
pandas
matplotlib
```

Default development dependencies:

```text
ipykernel
pytest
ruff
```

Install/synchronize:

```bash
uv sync --group dev
```

Add a package:

```bash
uv add scikit-learn
uv add torch
uv add transformers
```

Add a development-only package:

```bash
uv add --dev mypy
```

Run commands inside the environment:

```bash
uv run python ...
uv run pytest
uv run ruff check .
uv run ruff format .
```

---

## Lean project

To start with no runtime scientific dependencies:

```bash
ai-project my-project --lean
```

Then add only what is needed:

```bash
uv add numpy torch
```

---

# 8. Notebook architecture

Canonical notebook:

```text
notebooks/<name>.ipynb
```

Local editable mirror:

```text
.notebook/notebooks__<name>/<name>.ju.py
```

Example:

```text
notebooks/01_train.ipynb

↕ nbflow

.notebook/notebooks__01_train/
├── 01_train.ju.py
├── meta.json
├── AGENTS.md
├── run/
├── kaggle/
└── kaggle-output/
```

For nested notebook directories:

```text
notebooks/modeling/01_train.ipynb
```

the safe hidden directory becomes something like:

```text
.notebook/notebooks__modeling__01_train/
```

---

# 9. Why `.ju.py` exists

`.ipynb` is JSON.

Editing notebook JSON directly is inconvenient for:

- OpenCode
- Neovim
- diffs
- AI code edits
- cell-aware text editing

nbflow converts it into Jupytext percent format:

```python
# %% [markdown]
# # Experiment

# %%
import pandas as pd

# %%
df.head()
```

Cell boundaries are explicit through:

```text
# %%
```

Therefore OpenCode and Neovim work primarily with `.ju.py`.

---

# 10. Notebook source-of-truth rule

The committed/shareable artifact is:

```text
notebooks/**/*.ipynb
```

The `.ju.py` representation is local working state.

Therefore:

```text
.ipynb = canonical/shareable notebook
.ju.py = local editing representation
```

`.notebook/` is ignored by Git.

---

# 11. Main nbflow commands

## Create a new notebook

```bash
notebook create notebooks/01_eda.ipynb
```

This:

1. creates the canonical `.ipynb`
2. generates the `.ju.py`
3. creates `meta.json`
4. creates local `AGENTS.md`

---

## Register an existing notebook

```bash
notebook add notebooks/01_eda.ipynb
```

Use this when the `.ipynb` already exists.

---

## Edit

```bash
notebook edit notebooks/01_eda.ipynb
```

nbflow opens the corresponding `.ju.py` in `$EDITOR` or `nvim`.

---

## Sync `.ju.py → .ipynb`

From canonical path:

```bash
notebook sync notebooks/01_eda.ipynb
```

From the file currently being edited:

```bash
notebook sync-current \
  .notebook/notebooks__01_eda/01_eda.ju.py
```

This is the preferred OpenCode/Nvim flow.

---

## Pull `.ipynb → .ju.py`

```bash
notebook pull notebooks/01_eda.ipynb
```

Use when the canonical notebook changed externally.

For example:

- downloaded/updated from somewhere else
- manually changed through Jupyter
- changed after restoring a notebook version

The current `.ju.py` is backed up before regeneration.

`pull` also recreates `meta.json` when needed.

---

## Local execution

Canonical:

```bash
notebook run notebooks/01_eda.ipynb
```

Current `.ju.py`:

```bash
notebook run-current \
  .notebook/notebooks__01_eda/01_eda.ju.py
```

Executed notebooks are stored locally under:

```text
.notebook/.../run/
```

The canonical notebook is not replaced by the local executed copy.

---

## Status

```bash
notebook status notebooks/01_eda.ipynb
```

Shows mapping and Kaggle configuration.

---

## JupyterLab

```bash
notebook lab
```

or:

```bash
notebook lab --port 8889
```

---

# 12. Project-specific nbflow configuration

Each project can define:

```toml
[tool.nbflow]
kernel_name = "my_project"
kernel_display_name = "Python (my-project)"
kaggle_include = ["my_project"]
```

Meaning:

### `kernel_name`

Local Jupyter kernel identifier.

### `kernel_display_name`

Human-readable Jupyter kernel name.

### `kaggle_include`

Project-relative source files/directories that must travel with every Kaggle notebook.

Default new projects use:

```toml
kaggle_include = ["my_project"]
```

If configs are required:

```toml
kaggle_include = [
    "my_project",
    "configs",
]
```

Do not put large data/model directories here.

Bad:

```toml
kaggle_include = [
    "data",
    "models",
    ".venv",
]
```

---

# 13. Kaggle: the central problem

Locally, a notebook can do:

```python
from my_project.modeling.train import train_model
```

because `my_project/` exists on the machine.

But a Kaggle notebook upload fundamentally centers around the notebook code file.

Simply placing:

```text
01_train.ipynb
my_project/
```

in a temporary local directory is not sufficient for the project package to reliably become notebook source code on Kaggle.

Therefore nbflow creates a **self-contained Kaggle notebook**.

---

# 14. Kaggle code bundling

When pushing:

```bash
notebook kaggle-push notebooks/01_train.ipynb
```

nbflow does this:

```text
canonical notebook
        +
kaggle_include files
        ↓
compress project code
        ↓
encode archive
        ↓
generate hidden bootstrap cell
        ↓
create temporary Kaggle notebook
        ↓
Kaggle CLI push
```

The temporary upload notebook lives under:

```text
.notebook/notebooks__01_train/kaggle/01_train.ipynb
```

Its first cell is tagged:

```text
nbflow-bootstrap
```

The cell is generated automatically.

Do not edit it.

---

# 15. What the bootstrap cell does on Kaggle

At runtime it:

1. decodes the bundled project archive
2. extracts it into a temporary directory
3. adds the extraction directory to `sys.path`
4. also adds `src/` when present
5. sets environment helpers such as:

```text
NBFLOW_SOURCE_ROOT
NBFLOW_PROJECT_ROOT
```

Therefore code such as:

```python
from my_project.dataset import load_data
from my_project.modeling.train import train_model
```

continues to work on Kaggle.

The canonical notebook in:

```text
notebooks/
```

is never modified by this bootstrap.

---

# 16. Both package layouts are supported

Preferred new-project layout:

```text
my_project/
├── __init__.py
└── ...
```

Configuration:

```toml
kaggle_include = ["my_project"]
```

Existing projects may also use:

```text
src/
└── my_project/
    ├── __init__.py
    └── ...
```

Configuration:

```toml
kaggle_include = ["src/my_project"]
```

The bootstrap adds extracted `src/` to `sys.path` automatically.

---

# 17. Kaggle initialization

Kaggle configuration is notebook-specific and stored in:

```text
.notebook/<notebook-safe-name>/meta.json
```

Initialize once:

```bash
notebook kaggle-init notebooks/01_train.ipynb \
  --ref bachgia2604/project-01-train
```

Useful options:

```text
--title
--gpu
--internet
--public
--dataset
--competition
--kernel
--model
--include
```

Example:

```bash
notebook kaggle-init notebooks/01_train.ipynb \
  --ref bachgia2604/project-01-train \
  --gpu NvidiaTeslaT4 \
  --internet
```

GPU defaults to:

```text
none
```

---

# 18. Per-notebook extra source files

Global project source is defined through:

```toml
[tool.nbflow]
kaggle_include = ["my_project"]
```

A specific notebook can add extra paths:

```bash
notebook kaggle-init notebooks/01_train.ipynb \
  --ref bachgia2604/project-01-train \
  --include configs/train \
  --include assets/small_schema.json
```

This should be used only for small project code/config assets.

---

# 19. Push to Kaggle

From canonical notebook:

```bash
notebook kaggle-push notebooks/01_train.ipynb
```

From the current hidden text notebook:

```bash
notebook kaggle-push-current \
  .notebook/notebooks__01_train/01_train.ju.py
```

The second command is ideal for OpenCode/Nvim.

Both eventually perform:

```text
.ju.py
  ↓ sync
canonical .ipynb
  ↓ bundle current project code
temporary Kaggle .ipynb
  ↓
Kaggle
```

Optional:

```bash
notebook kaggle-push notebooks/01_train.ipynb --open
```

---

# 20. Kaggle status

```bash
notebook kaggle-status notebooks/01_train.ipynb
```

Use this before starting a downstream stage.

---

# 21. Download Kaggle output

```bash
notebook kaggle-output notebooks/01_train.ipynb
```

Downloaded output is stored under:

```text
.notebook/notebooks__01_train/kaggle-output/
```

---

# 22. Kaggle notebook pipeline

The intended research workflow is:

```text
00_prepare
    ↓ output becomes input
01_train
    ↓ output becomes input
02_evaluate
    ↓
03_results
```

This is intentionally a **notebook-stage pipeline**.

No Dagster/Prefect/Airflow is required unless the project later needs them.

---

# 23. Two independent dependency graphs

The workflow separates:

## Code dependency

```text
my_project/*.py
```

The current project code is bundled into **each notebook push**.

Example:

```text
01_train + current my_project code
02_evaluate + current my_project code
```

Notebook 02 does not import Python code from Notebook 01 output.

---

## Artifact dependency

Notebook-generated outputs travel through Kaggle notebook sources:

```text
Notebook 00 output
        ↓
Notebook 01 input

Notebook 01 output
        ↓
Notebook 02 input
```

This separation is important.

> Upstream notebook outputs contain data/model artifacts, not reusable source code.

---

# 24. Connecting Kaggle notebook stages

Assume:

```text
00_prepare
01_train
02_evaluate
```

## Stage 00

```bash
notebook kaggle-init notebooks/00_prepare.ipynb \
  --ref bachgia2604/project-00-prepare \
  --dataset owner/raw-dataset
```

This stage consumes the original dataset.

---

## Stage 01

```bash
notebook kaggle-init notebooks/01_train.ipynb \
  --ref bachgia2604/project-01-train \
  --kernel bachgia2604/project-00-prepare \
  --gpu NvidiaTeslaT4
```

`--kernel` here means:

> attach the output of another Kaggle notebook as an input source.

It corresponds to Kaggle `kernel_sources`.

It does **not** mean the local Jupyter kernel.

---

## Stage 02

If only Stage 01 output is needed:

```bash
notebook kaggle-init notebooks/02_evaluate.ipynb \
  --ref bachgia2604/project-02-evaluate \
  --kernel bachgia2604/project-01-train
```

If both Stage 00 and Stage 01 are read:

```bash
notebook kaggle-init notebooks/02_evaluate.ipynb \
  --ref bachgia2604/project-02-evaluate \
  --kernel bachgia2604/project-00-prepare \
  --kernel bachgia2604/project-01-train
```

Do not rely on transitive input availability.

Attach every upstream notebook whose output the current stage actually reads.

---

# 25. Kaggle artifact convention

A notebook should write durable results to:

```text
/kaggle/working/
```

Recommended structure:

```text
/kaggle/working/
└── artifacts/
    └── <stage>/
        ├── ...
        └── manifest.json
```

Example Stage 00:

```text
/kaggle/working/artifacts/00_prepare/
├── train.parquet
├── validation.parquet
├── test.parquet
└── manifest.json
```

Example Stage 01:

```text
/kaggle/working/artifacts/01_train/
├── model.pt
├── metrics.json
├── training_history.parquet
└── manifest.json
```

---

# 26. Artifact helper

New projects include:

```text
my_project/artifacts.py
```

Useful functions:

```python
from my_project.artifacts import (
    stage_dir,
    find_input,
    write_manifest,
)
```

---

## Write stage output

```python
output_dir = stage_dir("00_prepare")

train_path = output_dir / "train.parquet"
train_df.to_parquet(train_path)

write_manifest(
    "00_prepare",
    files={"train": train_path},
    rows=len(train_df),
)
```

---

## Find attached upstream input

Instead of hard-coding:

```python
Path("/kaggle/input/some-generated-mount-name/...")
```

use:

```python
train_path = find_input(
    "artifacts/00_prepare/train.parquet",
    source_hint="project-00-prepare",
)
```

This reduces dependence on Kaggle-generated mount names.

---

# 27. Local vs Kaggle paths

`config.py` distinguishes local and Kaggle execution.

Typical concepts:

```text
LOCAL:
data/
models/
reports/

KAGGLE INPUT:
/kaggle/input/

KAGGLE OUTPUT:
/kaggle/working/
```

When Kaggle is detected:

```text
INPUT_DIR  → /kaggle/input
OUTPUT_DIR → /kaggle/working
```

Therefore project code can be written once and used in both environments.

---

# 28. Running a Kaggle pipeline correctly

Do not push every stage at once.

Correct sequence:

```bash
notebook kaggle-push notebooks/00_prepare.ipynb
notebook kaggle-status notebooks/00_prepare.ipynb
```

Wait until successful.

Then:

```bash
notebook kaggle-push notebooks/01_train.ipynb
notebook kaggle-status notebooks/01_train.ipynb
```

Wait until successful.

Then:

```bash
notebook kaggle-push notebooks/02_evaluate.ipynb
notebook kaggle-status notebooks/02_evaluate.ipynb
```

The downstream stage should only start after the upstream stage has produced the expected output.

---

# 29. When to rerun downstream stages

Changing source code can invalidate previous artifacts.

Use this rule:

| Change | Rerun from |
|---|---|
| Raw data interpretation/schema | prepare |
| Train/validation/test split | prepare |
| Feature engineering | feature/preparation stage |
| Model architecture | train |
| Training logic/loss | train |
| Metric implementation | evaluate |
| Plot code | results/report stage |
| Markdown only | current notebook only |

Example:

```text
model architecture changed
```

Do not load an old checkpoint with the new model implementation unless compatibility is intentional.

---

# 30. Manifest as stage contract

Each stage should ideally produce:

```text
manifest.json
```

Basic example:

```json
{
  "stage": "01_train",
  "schema_version": 1,
  "files": {
    "checkpoint": "artifacts/01_train/model.pt",
    "metrics": "artifacts/01_train/metrics.json"
  }
}
```

For more rigorous research, extend it with:

```json
{
  "git_commit": "abc1234",
  "model_schema_version": 2,
  "dataset_version": "v3",
  "seed": 42
}
```

This makes artifact compatibility explicit.

---

# 31. Why notebook stages should not depend on hidden notebook state

Avoid:

```text
Run Notebook 00 in one kernel
↓
keep Python variables alive
↓
Notebook 01 assumes those variables still exist
```

Prefer:

```text
Notebook 00
↓
writes files
↓
Notebook 01
↓
reads files
```

This is required naturally on Kaggle and also improves reproducibility locally.

---

# 32. Git behavior

`ai-project` automatically initializes a Git repository and creates the initial commit.

The following are committed:

```text
notebooks/**/*.ipynb
project package
tests/
pyproject.toml
uv.lock
README.md
AGENTS.md
```

The following are local-only:

```text
.notebook/
.venv/
.ipynb_checkpoints/
*.executed.ipynb
```

Large/generated data/model files are ignored by default.

---

# 33. GitHub support

Create a project and push directly to GitHub:

```bash
ai-project my-project --github
```

Default GitHub repository visibility:

```text
private
```

Public repository:

```bash
ai-project my-project \
  --github \
  --github-public
```

Organization/user:

```bash
ai-project my-project \
  --github \
  --github-owner my-org
```

Prerequisite:

```bash
gh auth login
```

---

# 34. `ai-project` command reference

Basic:

```bash
ai-project my-project
```

Description:

```bash
ai-project my-project \
  --description "Cold-start recommendation experiments"
```

Choose Python:

```bash
ai-project my-project --python 3.12
```

Choose module:

```bash
ai-project my-project --module recommender
```

Lean environment:

```bash
ai-project my-project --lean
```

Custom first notebook:

```bash
ai-project my-project \
  --notebook 00_prepare.ipynb
```

No notebook:

```bash
ai-project my-project --no-notebook
```

Skip initial `uv sync`:

```bash
ai-project my-project --no-sync
```

GitHub:

```bash
ai-project my-project --github
```

Kaggle initialization:

```bash
ai-project my-project \
  --kaggle-ref bachgia2604/my-project
```

Kaggle GPU:

```bash
ai-project my-project \
  --kaggle-ref bachgia2604/my-project \
  --kaggle-gpu NvidiaTeslaT4
```

Kaggle internet:

```bash
ai-project my-project \
  --kaggle-ref bachgia2604/my-project \
  --kaggle-internet
```

---

# 35. Recommended new-project workflow

The shortest useful path is:

```bash
ai-project experiment-name --github
cd experiment-name
```

Then edit:

```bash
nvim \
  .notebook/notebooks__00_experiment-name/00_experiment-name.ju.py
```

Add dependencies only when needed:

```bash
uv add torch
uv add scikit-learn
```

Work normally.

---

# 36. Recommended daily notebook workflow

## 1. Edit the hidden notebook

```text
.notebook/**/<name>.ju.py
```

with OpenCode or Neovim.

## 2. Reusable implementation

Edit:

```text
my_project/**/*.py
```

## 3. Sync notebook

```bash
notebook sync-current <current.ju.py>
```

## 4. Optional local run

```bash
notebook run-current <current.ju.py>
```

## 5. Push Kaggle

```bash
notebook kaggle-push-current <current.ju.py>
```

## 6. Check status

```bash
notebook kaggle-status notebooks/<name>.ipynb
```

## 7. Run downstream stage when upstream succeeds

Repeat.

---

# 37. Example complete project pipeline

```text
project/
├── notebooks/
│   ├── 00_prepare.ipynb
│   ├── 01_train.ipynb
│   ├── 02_evaluate.ipynb
│   └── 03_results.ipynb
│
├── .notebook/
│   ├── notebooks__00_prepare/
│   ├── notebooks__01_train/
│   ├── notebooks__02_evaluate/
│   └── notebooks__03_results/
│
├── my_project/
│   ├── artifacts.py
│   ├── config.py
│   ├── dataset.py
│   ├── features.py
│   ├── plots.py
│   └── modeling/
│       ├── train.py
│       ├── predict.py
│       └── evaluate.py
│
├── data/
├── models/
├── reports/
├── tests/
├── AGENTS.md
├── pyproject.toml
└── uv.lock
```

Kaggle:

```text
raw dataset
    ↓
00_prepare
    ↓ artifacts/00_prepare/*
01_train
    ↓ artifacts/01_train/*
02_evaluate
    ↓ artifacts/02_evaluate/*
03_results
```

At every stage:

```text
current project Python code
          ↓ bundle
current Kaggle notebook
```

---

# 38. Creating additional notebooks

Example:

```bash
notebook create notebooks/01_train.ipynb
```

Then initialize Kaggle:

```bash
notebook kaggle-init notebooks/01_train.ipynb \
  --ref bachgia2604/project-01-train \
  --kernel bachgia2604/project-00-prepare \
  --gpu NvidiaTeslaT4
```

Edit:

```bash
notebook edit notebooks/01_train.ipynb
```

---

# 39. Existing project migration

Existing projects do not need to be recreated.

Add/merge:

```toml
[tool.nbflow]
kernel_name = "my_project"
kernel_display_name = "Python (my-project)"
kaggle_include = ["my_project"]
```

For `src/` layout:

```toml
[tool.nbflow]
kernel_name = "my_project"
kernel_display_name = "Python (my-project)"
kaggle_include = ["src/my_project"]
```

Existing `.notebook/**/meta.json` remains compatible.

If metadata is missing:

```bash
notebook pull notebooks/<name>.ipynb
```

---

# 40. Project-specific additions

The default scaffold is deliberately minimal.

Add these only when needed.

## Complex experiment configuration

Possible addition:

```text
configs/
```

and later Hydra if composition/sweeps become sufficiently complex.

---

## Experiment tracking

Start simple:

```text
JSON
CSV
Parquet
manifest.json
```

Add MLflow/W&B only when manual tracking becomes painful.

---

## Large/versioned datasets

Add DVC/object storage only when normal local/Kaggle data flow is no longer enough.

---

## Production API

Add:

```text
FastAPI
Docker
```

only when turning research code into a service.

---

## Scheduled workflows

Add:

```text
Dagster
Prefect
```

only when notebook-stage execution is no longer sufficient.

---

# 41. Important anti-patterns

Avoid editing:

```text
.ipynb JSON
```

directly.

Avoid committing:

```text
.notebook/
```

Avoid copying model/data functions across notebooks.

Avoid:

```python
sys.path.append("../../")
```

inside canonical notebooks merely to make imports work.

Avoid importing project source code from an upstream Kaggle notebook output.

Avoid storing huge datasets in `kaggle_include`.

Avoid hard-coding generated Kaggle input mount names when an artifact helper can resolve them.

Avoid starting downstream notebooks before upstream outputs are ready.

Avoid introducing DVC/MLflow/Hydra/Docker/etc. before there is a concrete need.

---

# 42. Troubleshooting

## `Missing meta.json`

Run:

```bash
notebook pull notebooks/<name>.ipynb
```

First make sure any unsynced `.ju.py` edits are backed up or synchronized.

---

## `.ju.py` missing

Register/regenerate:

```bash
notebook add notebooks/<name>.ipynb
```

or:

```bash
notebook pull notebooks/<name>.ipynb
```

---

## Kaggle ref missing

Initialize:

```bash
notebook kaggle-init notebooks/<name>.ipynb \
  --ref owner/slug
```

---

## Local import fails

Refresh environment:

```bash
uv sync --group dev
```

Check:

```bash
uv run python -c "import my_project; print(my_project)"
```

---

## Kaggle import fails

Check `pyproject.toml`:

```toml
[tool.nbflow]
kaggle_include = ["my_project"]
```

For src layout:

```toml
kaggle_include = ["src/my_project"]
```

Then push again.

---

## New Kaggle source/config is needed only for one notebook

Use:

```bash
notebook kaggle-init notebooks/<name>.ipynb \
  --ref owner/slug \
  --include path/to/resource
```

---

## Kaggle downstream cannot find upstream output

Check:

1. upstream notebook finished successfully
2. current notebook has correct `--kernel owner/upstream-slug`
3. file was written under `/kaggle/working`
4. relative artifact path is correct
5. `source_hint` matches the mounted upstream source

---

## Canonical notebook changed outside nbflow

Run:

```bash
notebook pull notebooks/<name>.ipynb
```

---

# 43. Verification commands

Project:

```bash
uv sync --group dev
uv run ruff check .
uv run pytest
```

Notebook:

```bash
notebook status notebooks/<name>.ipynb
notebook sync notebooks/<name>.ipynb
```

Kaggle:

```bash
notebook kaggle-status notebooks/<name>.ipynb
```

Global tools:

```bash
notebook --help
ai-project --help
```

---

# 44. Mental model

The entire setup can be remembered as:

```text
                 LOCAL
                  │
        ┌─────────┴─────────┐
        │                   │
 reusable .py code      .ju.py editing
        │                   │
        │               nbflow sync
        │                   ↓
        └────────────→ canonical .ipynb
                            │
                     nbflow Kaggle bundle
                            │
              ┌─────────────┴─────────────┐
              │                           │
       current project code          current notebook
              │                           │
              └─────────────┬─────────────┘
                            ↓
                        KAGGLE RUN
                            │
                    /kaggle/working
                            │
                      stage artifacts
                            │
                     kernel_sources
                            ↓
                    NEXT NOTEBOOK
```

And separately:

```text
Git
├── canonical notebooks
├── project Python code
├── pyproject.toml
├── uv.lock
├── tests
└── project instructions

Local-only
├── .notebook/
└── .venv/
```

---

# 45. Final operating principles

1. **Keep the scaffold small.**
2. **Use CCDS concepts, not every possible data-science tool.**
3. **Canonical notebooks are committed `.ipynb` files.**
4. **Edit notebooks through `.ju.py`.**
5. **Put reusable logic in `.py`.**
6. **Bundle current project code into each Kaggle push.**
7. **Pass only artifacts between Kaggle notebook stages.**
8. **Write durable Kaggle output under `/kaggle/working`.**
9. **Attach upstream notebook outputs explicitly.**
10. **Use `uv` for dependency/environment management.**
11. **Use Git by default; GitHub is one option on project creation.**
12. **Add project-specific infrastructure only when a real need appears.**

---

# 46. Minimal cheat sheet

```bash
# New project
ai-project my-project --github
cd my-project

# Add dependency
uv add torch

# New notebook
notebook create notebooks/01_train.ipynb

# Edit
notebook edit notebooks/01_train.ipynb

# Sync current hidden notebook
notebook sync-current .notebook/.../01_train.ju.py

# Local run
notebook run-current .notebook/.../01_train.ju.py

# Initialize Kaggle once
notebook kaggle-init notebooks/01_train.ipynb \
  --ref owner/project-01-train \
  --kernel owner/project-00-prepare \
  --gpu NvidiaTeslaT4

# Push current notebook + current project code
notebook kaggle-push-current .notebook/.../01_train.ju.py

# Check Kaggle
notebook kaggle-status notebooks/01_train.ipynb

# Download Kaggle output
notebook kaggle-output notebooks/01_train.ipynb

# Pull external canonical notebook changes back to text
notebook pull notebooks/01_train.ipynb

# Quality checks
uv run ruff check .
uv run pytest
```

---

## Status of this document

This README describes the current **nbflow v2.1 + ai-project + CCDS-style + uv + OpenCode/Neovim + chained Kaggle notebook** workflow.

When the tooling changes materially, update this file so it remains the single conceptual reference for the setup.
