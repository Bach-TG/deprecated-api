import json
from pathlib import Path
from typing import Any

from .config import ARTIFACTS_DIR, INPUT_DIR, IS_KAGGLE


def stage_dir(stage: str) -> Path:
    """Return and create the current stage's durable output directory."""
    path = ARTIFACTS_DIR / stage
    path.mkdir(parents=True, exist_ok=True)
    return path


def input_roots() -> list[Path]:
    """Return attached Kaggle input roots, or the local data directory."""
    if not IS_KAGGLE:
        return [INPUT_DIR]
    return sorted(path for path in INPUT_DIR.iterdir() if path.is_dir())


def find_input(relative_path: str | Path, source_hint: str | None = None) -> Path:
    """Find one attached upstream artifact without hard-coding mount names."""
    relative_path = Path(relative_path)
    matches = []
    for root in input_roots():
        if source_hint and source_hint not in root.name:
            continue
        candidate = root / relative_path
        if candidate.exists():
            matches.append(candidate)

    if not matches:
        raise FileNotFoundError(
            f"Input not found: {relative_path}; source_hint={source_hint!r}"
        )
    if len(matches) > 1:
        raise RuntimeError(
            f"Ambiguous input {relative_path}: "
            + ", ".join(str(path) for path in matches)
        )
    return matches[0]


def write_manifest(stage: str, files: dict[str, str | Path], **extra: Any) -> Path:
    """Write a small contract consumed by the next notebook stage."""
    output = stage_dir(stage) / "manifest.json"
    payload = {
        "stage": stage,
        "schema_version": 1,
        "files": {name: str(path) for name, path in files.items()},
        **extra,
    }
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return output
