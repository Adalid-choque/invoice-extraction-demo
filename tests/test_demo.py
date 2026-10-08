"""Automated tests: image validation, OCR baseline, API endpoints, data integrity."""
import csv
import io
import json
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from app.images import decode_image
from app.ocr import configure_tesseract, _find_nit, _find_fecha, _find_monto
from app.settings import DATA, ARTIFACTS, MAX_BYTES, FIELDS
from app.main import app


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_image_bytes(size=(128, 128), mode="RGB", fmt="JPEG"):
    buf = io.BytesIO()
    Image.new(mode, size, "white").save(buf, format=fmt)
    return buf.getvalue()


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# ── Data integrity ────────────────────────────────────────────────────────────

def test_annotations_csv_has_required_columns():
    rows = list(csv.DictReader(open(DATA / "annotations.csv")))
    assert len(rows) >= 199  # 199-200 depending on SIAT matches
    required = {"image_filename", "split", "tipo_foto", "nit", "fecha", "monto_total"}
    assert required.issubset(rows[0].keys())


def test_split_counts_are_correct():
    rows = list(csv.DictReader(open(DATA / "annotations.csv")))
    splits = {r["split"] for r in rows}
    assert splits == {"train", "validation", "test"}
    assert sum(1 for r in rows if r["split"] == "test") == 32


def test_test_images_exist_on_disk():
    rows = list(csv.DictReader(open(DATA / "annotations.csv")))
    for r in rows:
        if r["split"] == "test":
            assert (DATA / "images" / "test" / r["image_filename"]).exists(), \
                f"Missing: {r['image_filename']}"


def test_tipo_foto_values_are_valid():
    rows = list(csv.DictReader(open(DATA / "annotations.csv")))
    valid = {"bien_tomada", "con_sombra", "con_inclinacion"}
    for r in rows:
        assert r["tipo_foto"] in valid, f"Invalid tipo_foto: {r['tipo_foto']}"


# ── Image validation ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("fmt", ["JPEG", "PNG"])
def test_valid_image_accepted(fmt):
    img = decode_image(make_image_bytes(fmt=fmt))
    assert img.mode == "RGB"
    assert img.width >= 32 and img.height >= 32


def test_transparency_composited_on_white():
    buf = io.BytesIO()
    Image.new("RGBA", (64, 64), (0, 0, 0, 0)).save(buf, format="PNG")
    img = decode_image(buf.getvalue())
    assert img.mode == "RGB"
    assert img.getpixel((0, 0)) == (255, 255, 255)


def test_exif_orientation_applied():
    img = Image.new("RGB", (80, 40), "white")
    exif = img.getexif()
    exif[274] = 6  # rotate 90
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    result = decode_image(buf.getvalue())
    assert result.size == (40, 80)


@pytest.mark.parametrize("content", [
    b"",
    b"not an image",
    make_image_bytes(size=(10, 10)),   # too small
])
def test_invalid_images_rejected(content):
    with pytest.raises(ValueError):
        decode_image(content)


def test_oversize_file_rejected():
    with pytest.raises(ValueError):
        decode_image(b"0" * (MAX_BYTES + 1))


# ── OCR regex rules ───────────────────────────────────────────────────────────

def test_find_nit_extracts_digits():
    assert _find_nit("NIT: 5188252116") == "5188252116"


def test_find_nit_returns_empty_when_absent():
    assert _find_nit("sin numero aqui") == ""


@pytest.mark.parametrize("text,expected", [
    ("Fecha: 15/07/2026", "15/07/2026"),
    ("Fecha: 15-07-26",   "15/07/2026"),
    ("Fecha: 15.07.2026", "15/07/2026"),
])
def test_find_fecha_normalizes_separators(text, expected):
    assert _find_fecha(text) == expected


def test_find_monto_near_keyword():
    assert _find_monto("TOTAL Bs. 150.00") == "150.00"


def test_find_monto_returns_empty_when_absent():
    assert _find_monto("sin importe") == ""


# ── Artifacts ─────────────────────────────────────────────────────────────────

def test_metrics_json_exists_and_has_required_keys():
    data = json.loads((ARTIFACTS / "metrics.json").read_text())
    assert data["split"] == "test"
    assert data["images"] == 32
    assert set(data["metrics"].keys()) == {"gemini", "baseline"}
    for model in ["gemini", "baseline"]:
        for field in FIELDS:
            assert "exact_match" in data["metrics"][model][field]
            assert "cer" in data["metrics"][model][field]


def test_test_predictions_json_has_both_models():
    data = json.loads((ARTIFACTS / "test_predictions.json").read_text())
    assert "gemini" in data and "baseline" in data
    assert len(data["gemini"]) == 32
    assert len(data["baseline"]) == 32


# ── API endpoints ─────────────────────────────────────────────────────────────

def test_health_endpoint(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_metrics_endpoint_returns_data(client):
    r = client.get("/api/metrics")
    assert r.status_code == 200
    assert "metrics" in r.json()


def test_examples_endpoint_returns_list(client):
    r = client.get("/api/examples")
    assert r.status_code == 200
    examples = r.json()
    assert len(examples) >= 1
    assert "image_url" in examples[0]


def test_example_image_endpoint(client):
    examples = client.get("/api/examples").json()
    r = client.get(examples[0]["image_url"])
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("image/")


def test_unknown_example_returns_404(client):
    assert client.get("/api/examples/no_existe.jpeg/image").status_code == 404
    assert client.post("/api/examples/no_existe.jpeg/analyze").status_code == 404


def test_oversize_upload_returns_413(client):
    assert client.post("/api/analyze", content=b"a" * (MAX_BYTES + 1)).status_code == 413


def test_invalid_upload_returns_422(client):
    assert client.post("/api/analyze", content=b"not an image").status_code == 422


def test_concurrent_lock_returns_429(client):
    app.state.lock.acquire()
    try:
        r = client.post("/api/analyze", content=make_image_bytes())
        assert r.status_code == 429
    finally:
        app.state.lock.release()


def test_index_serves_html(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"<!DOCTYPE html>" in r.content or b"<html" in r.content
