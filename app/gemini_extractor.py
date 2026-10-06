"""Extract invoice fields using Gemini Vision-LLM. No fine-tuning applied.

Model: gemini-1.5-flash (Google AI Studio, free tier)
This model is used as-is without any additional training.
"""
import json
import os
import google.generativeai as genai
from PIL import Image

genai.configure(api_key=os.environ["GEMINI_API_KEY"])
_model = genai.GenerativeModel("models/gemini-3.8-flash")

_PROMPT = """Analiza esta imagen de una factura manuscrita boliviana.
Extrae exactamente estos tres campos:
- nit: solo los digitos del NIT o CI del cliente (sin puntos ni guiones)
- fecha: en formato DD/MM/YYYY
- monto_total: el importe total de la venta (solo numero, punto como decimal)

Responde UNICAMENTE con JSON valido, sin texto adicional ni explicaciones:
{"nit": "...", "fecha": "...", "monto_total": "..."}

Si no puedes leer un campo con certeza, usa cadena vacia "".
No inventes valores que no esten claramente visibles."""


def extract_fields(image_path: str) -> dict:
    """Send image to Gemini and return extracted invoice fields."""
    img      = Image.open(image_path)
    response = _model.generate_content([_PROMPT, img])
    text     = response.text.strip()
    text     = text.replace("```json", "").replace("```", "").strip()
    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        result = {}
    return {
        "nit":          str(result.get("nit", "")),
        "fecha":        str(result.get("fecha", "")),
        "monto_total":  str(result.get("monto_total", "")),
        "raw_response": text,
    }
