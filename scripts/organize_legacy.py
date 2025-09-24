from __future__ import annotations
import os
import shutil
from pathlib import Path

LEGACY_FILES = [
    "dropi_process.py",
    "fill_missing_statuses.py",
    "run_batches.py",
    "sheet_info.py",
]


def main() -> int:
    base = Path(__file__).resolve().parent
    legacy_dir = base / "_legacy"
    legacy_dir.mkdir(exist_ok=True)

    moved = []
    for name in LEGACY_FILES:
        src = base / name
        if src.exists() and src.is_file():
            dst = legacy_dir / name
            shutil.move(str(src), str(dst))
            moved.append(name)
    print(f"Moved: {moved}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
