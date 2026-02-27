"""Image preprocessing utilities."""
import io
from PIL import Image


def resize_image(image_bytes: bytes, max_size: int = 1024) -> bytes:
    """Resize image to fit within max_size x max_size while preserving aspect ratio."""
    img = Image.open(io.BytesIO(image_bytes))
    img.thumbnail((max_size, max_size), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def image_to_base64(image_bytes: bytes) -> str:
    import base64
    return base64.b64encode(image_bytes).decode("utf-8")
