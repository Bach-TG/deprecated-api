# deprecated-api

AI/Data Science project.

## Setup

```bash
uv sync --group dev
uv run python -m ipykernel install --user \
  --name deprecated_api \
  --display-name "Python (deprecated-api)"
```

## Notebook

Canonical notebooks are committed under `notebooks/`. Editable Jupytext files,
local execution results, and Kaggle metadata are generated under `.notebook/`.


```bash
notebook edit notebooks/00_deprecated-api.ipynb
notebook run notebooks/00_deprecated-api.ipynb
```


## Quality checks

```bash
uv run ruff check .
uv run pytest
```
