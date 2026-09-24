# Project instructions

## Structure

- Follow the lightweight Cookiecutter Data Science structure.
- Canonical, committed notebooks live under `notebooks/`.
- Local nbflow/Jupytext files live under `.notebook/` and are ignored.
- Reusable project code lives under `deprecated_api/`.
- Raw data is immutable. Derived data belongs in `data/interim/` or
  `data/processed/`.
- Generated model artifacts belong in `models/`.
- Generated report figures belong in `reports/figures/`.

## Notebook boundaries

- Use notebooks for exploration, experiments, visualization, and presentation.
- Move reusable data, feature, model, training, prediction, metric, and plotting
  logic into `deprecated_api/`.
- Notebooks may import project code; project code must never import notebooks.
- Avoid hidden notebook-to-notebook state dependencies. Exchange results through
  explicit files under `data/`, `models/`, or `reports/` locally and through
  `/kaggle/working` outputs on Kaggle.
- Each Kaggle stage must write deterministic artifacts and a manifest for the
  next stage. Read attached notebook outputs from `/kaggle/input` through the
  project artifact helpers instead of hard-coding generated mount names.
- Import project code bundled into the current notebook push. Do not import code
  from a previous notebook's output; upstream notebook sources carry data/model
  artifacts only.

The personal editing, synchronization, execution, and Kaggle commands are defined
globally in `~/.config/opencode/AGENTS.md`.

## Commands

- Add a dependency: `uv add <package>`
- Add a development dependency: `uv add --dev <package>`
- Refresh the environment: `uv sync --group dev`
- Lint: `uv run ruff check .`
- Format: `uv run ruff format .`
- Test: `uv run pytest`

## Kaggle packaging

`[tool.nbflow].kaggle_include` in `pyproject.toml` lists local project paths
uploaded with every Kaggle notebook. The project package is included by default.
Add paths such as `configs` only when a notebook actually needs them.
