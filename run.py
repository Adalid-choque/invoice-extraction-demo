"""Start the invoice extraction demo."""
import argparse
import os
import subprocess
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8998)
    args = parser.parse_args()

    if not os.environ.get("GEMINI_API_KEY"):
        raise SystemExit("Falta GEMINI_API_KEY en el archivo .env")

    for filename in ["metrics.json", "test_predictions.json"]:
        if not (ROOT / "artifacts" / filename).exists():
            raise SystemExit(
                f"Falta artifacts/{filename}. "
                f"Ejecuta primero: python -m app.evaluate"
            )

    from app.ocr import configure_tesseract
    configure_tesseract()

    print(f"Abre http://127.0.0.1:{args.port}  -  Ctrl+C detiene el servidor.")
    subprocess.run(
        [sys.executable, "-m", "uvicorn", "app.main:app",
         "--host", "127.0.0.1", "--port", str(args.port)],
        cwd=ROOT, check=True,
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
