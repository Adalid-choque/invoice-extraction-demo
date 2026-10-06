"""Evaluate both models on the test split. Run once; never retrain after."""
import csv
import json
import time
from datetime import datetime, timezone
from dotenv import load_dotenv
load_dotenv()
from jiwer import cer as compute_cer
from app.gemini_extractor import extract_fields
from app.ocr import extract_fields_baseline, configure_tesseract
from app.settings import DATA, ARTIFACTS, FIELDS


def _norm(v: str) -> str:
    """Normalize value for comparison: lowercase, strip, unify separators."""
    return str(v).strip().lower().replace("-", "/").replace(".", "/").replace(",", ".").replace(" ", "")


def _em(pred: str, ref: str) -> int:
    return int(_norm(pred) == _norm(ref))


def _cer(ref: str, pred: str) -> float:
    r, p = _norm(ref), _norm(pred)
    if not r:
        return 0.0 if not p else 1.0
    try:
        return compute_cer(r, p)
    except Exception:
        return 1.0


def main():
    configure_tesseract()
    all_rows  = list(csv.DictReader(open(DATA / "annotations.csv")))
    test_rows = [r for r in all_rows if r["split"] == "test"]
    print(f"Evaluating {len(test_rows)} test images...")

    results = {f: {"gemini": [], "baseline": []} for f in FIELDS}
    g_preds = {}
    b_preds = {}

    started = time.perf_counter()
    for i, row in enumerate(test_rows, 1):
        path = str(DATA / "images" / "test" / row["image_filename"])

        # Wait BEFORE calling Gemini to stay under 4 req/min (15s spacing)
        if i > 1:
            print(f"  Waiting 15s before next Gemini call...", flush=True)
            time.sleep(15)

        g = {"nit": "", "fecha": "", "monto_total": "", "raw_response": ""}
        for attempt in range(3):
            try:
                g = extract_fields(path)
                break
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    wait = 30 * (attempt + 1)  # 30s, 60s, 90s
                    print(f"  Rate limit, waiting {wait}s (attempt {attempt+1})...", flush=True)
                    time.sleep(wait)
                else:
                    print(f"  Gemini error: {e}", flush=True)
                    break

        b = extract_fields_baseline(path)
        g_preds[row["image_filename"]] = g
        b_preds[row["image_filename"]] = b

        for f in FIELDS:
            ref = row.get(f, "")
            results[f]["gemini"].append({
                "id": row["image_filename"], "ref": ref,
                "pred": g.get(f, ""),
                "exact_match": _em(g.get(f, ""), ref),
                "cer": _cer(ref, g.get(f, "")),
            })
            results[f]["baseline"].append({
                "id": row["image_filename"], "ref": ref,
                "pred": b.get(f, ""),
                "exact_match": _em(b.get(f, ""), ref),
                "cer": _cer(ref, b.get(f, "")),
            })
        print(f"  {i}/{len(test_rows)}  {row['image_filename']}", flush=True)

    # Summarize metrics
    metrics = {}
    for model in ["gemini", "baseline"]:
        metrics[model] = {}
        for f in FIELDS:
            rs = results[f][model]
            metrics[model][f] = {
                "exact_match": round(sum(r["exact_match"] for r in rs) / len(rs), 3),
                "cer":         round(sum(r["cer"]         for r in rs) / len(rs), 3),
                "n":           len(rs),
            }
        ems = [metrics[model][f]["exact_match"] for f in FIELDS]
        metrics[model]["macro_exact_match"] = round(sum(ems) / len(ems), 3)

    report = {
        "created_at":      datetime.now(timezone.utc).isoformat(),
        "split":           "test",
        "images":          len(test_rows),
        "fields":          FIELDS,
        "metrics":         metrics,
        "elapsed_seconds": round(time.perf_counter() - started, 2),
    }

    ARTIFACTS.mkdir(exist_ok=True)
    (ARTIFACTS / "metrics.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    )
    (ARTIFACTS / "test_predictions.json").write_text(
        json.dumps({"gemini": g_preds, "baseline": b_preds},
                   indent=2, ensure_ascii=False) + "\n"
    )
    print("\n=== RESULTADOS ===")
    print(json.dumps(metrics, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
