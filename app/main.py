"""Local HTTP interface. Images are processed in memory and never saved."""
import csv
import json
import tempfile
import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from app.images import decode_image
from app.pipeline import Pipeline
from app.settings import ROOT, ARTIFACTS, DATA, MAX_BYTES


def _load_examples():
    """Load up to 2 examples per tipo_foto from the test split."""
    rows = list(csv.DictReader(open(DATA / "annotations.csv")))
    test = [r for r in rows if r["split"] == "test"]
    seen = {}
    for tipo in ["bien_tomada", "con_sombra", "con_inclinacion"]:
        subset = [r for r in test if r.get("tipo_foto") == tipo][:2]
        for r in subset:
            seen[r["image_filename"]] = r
    return seen


@asynccontextmanager
async def lifespan(app):
    app.state.pipeline = Pipeline()
    app.state.lock     = threading.Lock()
    app.state.metrics  = json.loads((ARTIFACTS / "metrics.json").read_text())
    app.state.examples = _load_examples()
    yield


app = FastAPI(title="Extracción de Facturas · Vision-LLM", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(ROOT / "frontend")), name="static")


@app.get("/")
def index():
    return FileResponse(ROOT / "frontend/index.html")


@app.get("/api/health")
def health():
    return {"status": "ok", "model": "gemini-3.8-flash", "baseline": "tesseract+regex"}


@app.get("/api/metrics")
def metrics():
    return app.state.metrics


@app.get("/api/examples")
def examples():
    return [
        {
            "id":          r["image_filename"],
            "num_factura": r["num_factura"],
            "tipo_foto":   r.get("tipo_foto", ""),
            "image_url":   f"/api/examples/{r['image_filename']}/image",
        }
        for r in app.state.examples.values()
    ]


@app.get("/api/examples/{filename}/image")
def example_image(filename: str):
    row = app.state.examples.get(filename)
    if not row:
        raise HTTPException(404, "Ejemplo no disponible.")
    path = DATA / "images" / "test" / filename
    return Response(path.read_bytes(), media_type="image/jpeg")


async def _analyze(content: bytes):
    """Validate image and run both models."""
    if len(content) > MAX_BYTES:
        raise HTTPException(413, "La imagen supera el límite de 5 MB.")
    try:
        image = decode_image(content)
    except ValueError as e:
        raise HTTPException(422, str(e))
    if not app.state.lock.acquire(blocking=False):
        raise HTTPException(429, "Hay un análisis en curso. Espera unos segundos.")
    try:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            image.save(tmp.name)
            path = tmp.name
        return await run_in_threadpool(app.state.pipeline.analyze, path)
    finally:
        app.state.lock.release()


@app.post("/api/examples/{filename}/analyze")
async def analyze_example(filename: str):
    row = app.state.examples.get(filename)
    if not row:
        raise HTTPException(404, "Ejemplo no disponible.")
    return await _analyze((DATA / "images" / "test" / filename).read_bytes())


@app.post("/api/analyze")
async def analyze_upload(request: Request):
    content = bytearray()
    async for chunk in request.stream():
        content.extend(chunk)
        if len(content) > MAX_BYTES:
            raise HTTPException(413, "La imagen supera el límite de 5 MB.")
    return await _analyze(bytes(content))
