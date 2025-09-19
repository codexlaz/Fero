"""Application package initialization."""
from pathlib import Path

RHYTHMS_ROOT = Path(__file__).resolve().parent.parent / "rhythms"
RHYTHMS_ROOT.mkdir(exist_ok=True)

__all__ = ["RHYTHMS_ROOT"]
