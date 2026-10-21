"""Profile the raw dataset: columns, dtypes, null rates and sample values."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.stdout.reconfigure(encoding="utf-8")

from zomato_reco.ingestion.loader import load_raw  # noqa: E402

df = load_raw()
print(f"rows={len(df)} cols={len(df.columns)}\n")
for col in df.columns:
    s = df[col]
    sample = [str(v)[:60] for v in s.dropna().unique()[:5]]
    print(f"- {col!r}: dtype={s.dtype} nulls={s.isna().sum()} unique={s.nunique()} sample={sample}")
