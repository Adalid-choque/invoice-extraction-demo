"""Image decoding and validation."""
import io
from PIL import Image, ImageOps
from app.settings import MAX_BYTES, MAX_PIXELS


def decode_image(content: bytes) -> Image.Image:
    """Validate and decode image bytes to a PIL Image."""
    if len(content) > MAX_BYTES:
        raise ValueError("El archivo supera 5 MB.")
    try:
        img = Image.open(io.BytesIO(content))
        img.verify()
        img = Image.open(io.BytesIO(content))
    except Exception:
        raise ValueError("El archivo no es una imagen válida (PNG o JPEG).")
    img = ImageOps.exif_transpose(img)
    if img.width < 32 or img.height < 32:
        raise ValueError("La imagen es demasiado pequeña (mínimo 32×32 píxeles).")
    if img.width * img.height > MAX_PIXELS:
        raise ValueError("La imagen supera 12 megapíxeles.")
    if img.mode in ("RGBA", "LA", "P"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        mask = img.split()[-1] if img.mode in ("RGBA", "LA") else None
        bg.paste(img, mask=mask)
        img = bg
    return img.convert("RGB")
