"""Build annotations.csv from SIAT export and image folders."""
import os
import csv
import pandas as pd

SIAT_FILE = "data/ventas-5188252116-01-07-2026-31-07-2026.csv"

# Folder name → tipo_foto label
TIPO_MAP = {
    "train":      "",   # filled below per image
    "validation": "",
    "test":       "",
}

# Which invoice numbers belong to which tipo_foto
# Based on folder structure: normales=1222-1360, sombra=1311-1350, inclinacion=1361-1400
def get_tipo(num_str):
    try:
        n = int(num_str)
        if 1311 <= n <= 1350:
            return "con_sombra"
        elif 1361 <= n <= 1400:
            return "con_inclinacion"
        else:
            return "bien_tomada"
    except Exception:
        return "bien_tomada"


# Load SIAT export
df = pd.read_csv(SIAT_FILE, sep=";", dtype=str)
df.columns = df.columns.str.strip()
print("Columnas del CSV:", list(df.columns))

df["num_factura"] = df["N° DE LA FACTURA"].str.strip()

# Collect all images with their split
rows = []
for split in ["train", "validation", "test"]:
    folder = os.path.join("data", "images", split)
    if not os.path.exists(folder):
        continue
    for fname in sorted(os.listdir(folder)):
        if not fname.lower().endswith((".jpg", ".jpeg", ".png")):
            continue
        # Extract invoice number: factura_1222_1.jpeg → 1222
        stem  = fname.rsplit(".", 1)[0]       # factura_1222_1
        parts = stem.split("_")               # ['factura','1222','1']
        num   = parts[1] if len(parts) >= 2 else stem
        rows.append({
            "image_filename": fname,
            "num_factura":    num,
            "split":          split,
            "tipo_foto":      get_tipo(num),
        })

img_df = pd.DataFrame(rows)
print(f"Imágenes encontradas: {len(img_df)}")

# Merge with SIAT data
merged = img_df.merge(df, on="num_factura", how="left")

# Build final CSV
out = pd.DataFrame({
    "image_filename": merged["image_filename"],
    "num_factura":    merged["num_factura"],
    "split":          merged["split"],
    "tipo_foto":      merged["tipo_foto"],
    "fecha":          merged.get("FECHA DE LA FACTURA", pd.Series(dtype=str)).fillna(""),
    "nit":            merged.get("NIT / CI CLIENTE", pd.Series(dtype=str)).fillna("").astype(str).str.strip(),
    "razon_social":   merged.get("NOMBRE O RAZON SOCIAL", pd.Series(dtype=str)).fillna(""),
    "monto_total":    merged.get("IMPORTE TOTAL DE LA VENTA", pd.Series(dtype=str)).fillna("").astype(str),
})

out.to_csv("data/annotations.csv", index=False)
print(f"\n✅ Generado: data/annotations.csv con {len(out)} filas")
print(f"\nDistribución:")
print(out["split"].value_counts().to_string())
print(f"\nTipo de foto:")
print(out["tipo_foto"].value_counts().to_string())
print(f"\nPrimeras 5 filas del conjunto de prueba:")
print(out[out["split"]=="test"][["image_filename","nit","fecha","monto_total"]].head(5).to_string())
