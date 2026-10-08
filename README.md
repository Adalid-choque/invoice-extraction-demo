# Extracción de Facturas · Vision-LLM vs Tesseract

Ejemplo educativo de extracción de campos en facturas manuscritas bolivianas. Compara un modelo Vision-LLM (Gemini) contra una línea base de OCR clásico (Tesseract + regex) para extraer NIT, fecha y monto total.

El código, las variables y los comentarios están en inglés. La interfaz y esta documentación están en español. No contiene nombres de alumnos ni imágenes de personas.

## El caso de uso

Un estudio contable recibe fotos de facturas manuscritas. Queremos extraer automáticamente tres campos por factura:

| Campo en el código | Significado |
|---|---|
| `nit` | NIT o CI del cliente |
| `fecha` | Fecha de emisión (DD/MM/YYYY) |
| `monto_total` | Importe total de la venta en bolivianos |

Es **extracción de información**, no clasificación. Cada modelo devuelve texto, no una categoría.

## Abrir el ejemplo

Requisito: **Python 3.10+**, **Tesseract OCR 5+** instalado en el sistema y una clave de API de Google AI Studio en el archivo `.env`.

```
GEMINI_API_KEY=tu_clave_aqui
```

Windows PowerShell:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py
```

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

Abre **http://127.0.0.1:8998**. Mantén la terminal abierta; `Ctrl+C` detiene el servidor.

Para otro puerto: `python run.py --port 8999`.

## Qué puedes probar

1. Selecciona una factura de la colección y pulsa **Analizar**.
2. Compara los campos extraídos por Gemini y Tesseract.
3. Observa el aviso de revisión cuando los modelos no coinciden.
4. Sube tu propio PNG o JPEG de una factura.
5. Abre la sección de métricas para ver los resultados en el conjunto de prueba.

Las imágenes subidas se procesan en memoria y no se guardan. Se aceptan archivos de hasta 5 MB, de 32×32 píxeles o más, hasta 12 megapíxeles y proporción entre 1:2 y 2:1.

## Datos

| Elemento | Configuración |
|---|---|
| Origen | Estudio Contable Ugarte & Asociados, Cochabamba, Bolivia |
| Total | 199 fotos de facturas manuscritas reales |
| Entrenamiento | ~140 imágenes |
| Validación | ~27 imágenes |
| Prueba | 32 imágenes |
| Tipos de foto | Normal, con sombra/luz tenue, con ligera inclinación |
| Ground truth | Exportación SIAT (sistema tributario boliviano) |

Las seis imágenes de una misma factura permanecen en una sola partición para evitar fuga de datos. Ni Gemini ni Tesseract reciben el nombre del archivo como entrada.

## Modelos

**Gemini (modelo principal):** `models/gemini-3.8-flash` vía Google AI Studio. Recibe la imagen completa y un prompt que solicita JSON con los tres campos. No se aplica fine-tuning; se usa el modelo tal como está disponible en el plan gratuito.

**Tesseract (línea base):** OCR clásico con `--psm 6` en escala de grises con autocontraste. Extrae texto y aplica regex para NIT (7–13 dígitos), fecha (patrones DD/MM/YYYY) y monto (número cerca de palabras clave como "total", "importe").

## Resultados obtenidos

| Métrica | Gemini | Tesseract |
|---|---:|---:|
| Exact Match NIT | 0.000 | 0.000 |
| Exact Match Fecha | 0.000 | 0.000 |
| Exact Match Monto | 0.000 | 0.000 |
| Macro Exact Match | 0.000 | 0.000 |
| CER Fecha | 1.000 | 0.697 |

Los resultados de Gemini reflejan una ejecución afectada por límites de cuota del plan gratuito (5 peticiones/minuto): la mayoría de las llamadas devolvieron respuesta vacía por errores 429. Los resultados de Tesseract son reales pero muestran las limitaciones del OCR clásico ante escritura manuscrita irregular.

Los resultados completos están en [artifacts/metrics.json](artifacts/metrics.json) y las predicciones individuales en [artifacts/test_predictions.json](artifacts/test_predictions.json).

## Reproducir la evaluación

Con el entorno activado y la clave en `.env`:

```bash
python -m app.evaluate
python -m pytest -q
python run.py
```

`evaluate` procesa las 32 imágenes del conjunto de prueba con ambos modelos y guarda los artefactos. Con el plan gratuito de Gemini tarda aproximadamente 8–10 minutos (pausa de 15 s entre llamadas para respetar el límite de cuota).

## Estructura

```
invoice-extraction-demo/
├── README.md
├── run.py                  # Punto de entrada: verifica .env y arranca uvicorn
├── requirements.txt
├── app/
│   ├── settings.py         # Rutas y constantes compartidas
│   ├── gemini_extractor.py # Modelo principal: Gemini Vision-LLM
│   ├── ocr.py              # Línea base: Tesseract + regex
│   ├── pipeline.py         # Ejecuta ambos modelos y detecta desacuerdos
│   ├── images.py           # Validación y decodificación de imágenes
│   ├── evaluate.py         # Evaluación sobre el conjunto de prueba
│   └── main.py             # API FastAPI
├── frontend/               # HTML, CSS y JavaScript sin compilación
├── data/
│   ├── annotations.csv     # Etiquetas, splits y tipo de foto por imagen
│   └── images/             # train / validation / test
├── artifacts/              # metrics.json y test_predictions.json
├── scripts/
│   └── build_annotations.py
└── tests/
    └── test_demo.py
```

## Límites que debes considerar

- Gemini en plan gratuito tiene un límite estricto de peticiones por minuto. En producción se requiere un plan de pago o caché de resultados.
- Los modelos siempre devuelven algún valor; no detectan si la imagen no es una factura.
- El aviso de revisión usa desacuerdo entre modelos como señal ilustrativa, no como umbral validado para uso real.
- Las fotos provienen de un solo estudio contable. Los resultados no generalizan a otros formatos de factura sin reentrenamiento o ajuste del prompt.
- El ground truth del SIAT puede tener discrepancias menores con lo escrito a mano en la factura física.

## Si algo no funciona

- **No abre la página:** espera `Uvicorn running` y conserva la terminal abierta.
- **Puerto ocupado:** usa `--port 8999`.
- **KeyError GEMINI_API_KEY:** verifica que el archivo `.env` existe en la raíz del proyecto con la clave correcta.
- **Tesseract no encontrado:** instala Tesseract 5+ y agrega `TESSERACT_CMD=ruta/al/binario` al `.env` si no está en el PATH.
- **Falta metrics.json:** ejecuta `python -m app.evaluate` antes de `run.py`.
