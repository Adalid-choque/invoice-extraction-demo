"""Shared paths and limits."""
from pathlib import Path

ROOT      = Path(__file__).resolve().parent.parent
DATA      = ROOT / "data"
ARTIFACTS = ROOT / "artifacts"
MAX_BYTES  = 5 * 1024 * 1024
MAX_PIXELS = 12_000_000
FIELDS     = ["nit", "fecha", "monto_total"]
