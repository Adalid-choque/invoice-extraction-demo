"""Run Gemini (main model) and Tesseract (baseline) on the same image."""
import time
from app.gemini_extractor import extract_fields
from app.ocr import extract_fields_baseline, configure_tesseract


class Pipeline:
    def __init__(self):
        configure_tesseract()

    def analyze(self, image_path: str) -> dict:
        """Return extraction results from both models for comparison."""
        started  = time.perf_counter()
        gemini   = extract_fields(image_path)
        baseline = extract_fields_baseline(image_path)
        # Suggest review if models disagree on any field or Gemini confidence is low
        fields = ["nit", "fecha", "monto_total"]
        disagree = any(gemini.get(f, "") != baseline.get(f, "") for f in fields)
        low_conf = float(gemini.get("confidence", 1.0)) < 0.70
        review_flag = disagree or low_conf
        return {
            "gemini":        gemini,
            "baseline":      baseline,
            "elapsed_ms":    round((time.perf_counter() - started) * 1000),
            "review_flag":   review_flag,
            "review_reason": "desacuerdo entre modelos" if disagree else "confianza baja en Gemini",
        }
