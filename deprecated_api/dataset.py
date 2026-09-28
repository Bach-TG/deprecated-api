"""Benchmark file loading and the original per-(library, category) cap."""

import json
import random
from pathlib import Path

from .artifacts import find_input
from .config import IS_KAGGLE, RAW_DATA_DIR


def benchmark_file(name, data_dir=None):
    if data_dir is not None:
        path = Path(data_dir) / name
    elif IS_KAGGLE:
        path = find_input(name)
    else:
        path = RAW_DATA_DIR / name
    if not path.is_file():
        raise FileNotFoundError(
            f"Missing benchmark file {path}. Place benchmark JSON files in data/raw/ locally, "
            "or attach the benchmark dataset explicitly on Kaggle. "
            "SPLIT='full' requires sample_full.json."
        )
    return path


def load_benchmark(split="sample", limit=0, sample_seed=42, data_dir=None):
    split_files = {"sample": "sample.json", "smoke": "smoke.json", "full": "sample_full.json"}
    if split not in split_files:
        raise ValueError(f"Unknown split {split!r}; choose sample, smoke, or full")
    required = ["mappings.json", "sample.json", "smoke.json", "humaneval.json"]
    if split == "full":
        required.append("sample_full.json")
    data = {}
    for name in required:
        with benchmark_file(name, data_dir).open(encoding="utf-8") as f:
            data[name] = json.load(f)
    items = data[split_files[split]]
    if limit > 0:
        rng = random.Random(sample_seed)
        shuffled = items[:]
        rng.shuffle(shuffled)
        counts, capped = {}, []
        for it in shuffled:
            key = (it["lib"], it["category"])
            if counts.get(key, 0) < limit:
                counts[key] = counts.get(key, 0) + 1
                capped.append(it)
        items = capped
    print(
        f"{len(data['mappings.json'])} API mappings, "
        f"{len(items)} prompts from {split!r} (limit={limit}, seed={sample_seed})"
    )
    return data["mappings.json"], items, data["humaneval.json"]
