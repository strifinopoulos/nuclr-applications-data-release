#!/usr/bin/env python3
"""Regenerate MANIFEST.csv for source and release files."""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_TOP_LEVEL = {".git", "reproduced"}


def included(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    return (
        path.is_file()
        and path.name != "MANIFEST.csv"
        and "__pycache__" not in relative.parts
        and path.suffix.lower() not in {".pyc", ".pyo"}
        and relative.parts[0] not in EXCLUDED_TOP_LEVEL
        and not relative.parts[0].startswith("tmp_")
    )


def main() -> None:
    rows = []
    for path in sorted((path for path in ROOT.rglob("*") if included(path))):
        relative = path.relative_to(ROOT).as_posix()
        data_rows = ""
        if path.suffix.lower() == ".csv":
            with path.open("r", encoding="utf-8", errors="replace") as handle:
                data_rows = max(sum(1 for _ in handle) - 1, 0)
        rows.append(
            {
                "path": relative,
                "bytes": path.stat().st_size,
                "data_rows": data_rows,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    with (ROOT / "MANIFEST.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["path", "bytes", "data_rows", "sha256"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} entries to MANIFEST.csv")


if __name__ == "__main__":
    main()
