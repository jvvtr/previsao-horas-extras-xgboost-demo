"""Regenerate every public artifact from deterministic synthetic data."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from demo_pipeline import build_demo  # noqa: E402

if __name__ == "__main__":
    result = build_demo(ROOT / "artifacts")
    print(f"Demonstração sintética pronta: {result['tree_count']} árvores.")
