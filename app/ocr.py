"""Baseline extraction: Tesseract OCR + regex rules. No machine learning."""
import os
import re
import shutil
import pytesseract
from PIL import Image, ImageOps


def configure_tesseract():
    """Locate Tesseract binary."""
    binary = os.environ.get("TESSERACT_CMD") or shutil.which("tesseract")
    if not binary:
        binary = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if not os.path.isfile(str(binary)):
        raise RuntimeError(
            "Tesseract no encontrado. Instálalo y agrega TESSERACT_CMD al .env si es necesario."
        )
    pytesseract.pytesseract.tesseract_cmd = str(binary)


def extract_fields_baseline(image_path: str) -> dict:
    """Extract invoice fields using Tesseract + regex (declared baseline)."""
    img = ImageOps.autocontrast(Image.open(image_path).convert("L"))
    try:
        text = pytesseract.image_to_string(img, lang="spa", config="--psm 6")
    except Exception:
        text = ""
    return {
        "nit":         _find_nit(text),
        "fecha":       _find_fecha(text),
        "monto_total": _find_monto(text),
        "raw_text":    text,
    }


def _find_nit(text: str) -> str:
    m = re.search(r'\b(\d{7,13})\b', text)
    return m.group(1) if m else ""


def _find_fecha(text: str) -> str:
    m = re.search(r'\b(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})\b', text)
    if not m:
        return ""
    v = m.group(1).replace("-", "/").replace(".", "/")
    p = v.split("/")
    if len(p) == 3 and len(p[2]) == 2:
        p[2] = "20" + p[2]
    return "/".join(p)


def _find_monto(text: str) -> str:
    m = re.search(
        r'(?:total|importe|monto)[^\d]{0,20}(\d{1,6}[.,]\d{2})',
        text, re.IGNORECASE
    )
    if not m:
        m = re.search(r'\b(\d{1,6}[.,]\d{2})\b', text)
    return m.group(1).replace(",", ".") if m else ""
