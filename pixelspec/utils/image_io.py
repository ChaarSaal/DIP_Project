"""
PixelSpec Image Input/Output and Utility Functions
Robust decoding, color transformations, EXIF orientation correction, and serialization.
"""

import io
import base64
from typing import Tuple, List, Optional
import numpy as np
import cv2
from PIL import Image, ImageOps


def load_image_bytes(data: bytes) -> Tuple[np.ndarray, List[str]]:
    """
    Decodes raw image bytes into an RGB numpy uint8 array with EXIF orientation correction.
    Returns (rgb_image, processing_notes).
    """
    notes = []
    try:
        pil_img = Image.open(io.BytesIO(data))
    except Exception as e:
        raise ValueError(f"Failed to decode image data: {str(e)}")

    # Handle EXIF orientation
    try:
        oriented = ImageOps.exif_transpose(pil_img)
        if oriented is not None:
            pil_img = oriented
            notes.append("EXIF orientation applied.")
    except Exception:
        pass

    # Handle color modes
    if pil_img.mode == "RGBA":
        # Alpha compositing against standard pure white background (e-commerce standard)
        bg = Image.new("RGB", pil_img.size, (255, 255, 255))
        bg.paste(pil_img, mask=pil_img.split()[3])
        pil_img = bg
        notes.append("Composited RGBA transparency onto pure white (255, 255, 255).")
    elif pil_img.mode != "RGB":
        pil_img = pil_img.convert("RGB")
        notes.append(f"Converted image mode from {pil_img.mode} to RGB.")

    rgb = np.array(pil_img, dtype=np.uint8)
    return rgb, notes


def image_to_base64_png(image_array: np.ndarray) -> str:
    """
    Converts a uint8 numpy array (RGB, Grayscale, or Binary mask) into a base64 PNG data URI string.
    """
    if image_array.ndim == 2:
        # Check if binary mask
        if image_array.dtype == bool:
            img_to_encode = (image_array.astype(np.uint8) * 255)
        else:
            img_to_encode = image_array
        pil_img = Image.fromarray(img_to_encode)
    elif image_array.ndim == 3:
        pil_img = Image.fromarray(image_array)
    else:
        raise ValueError("Unsupported array dimensions for image serialization.")

    buf = io.BytesIO()
    pil_img.save(buf, format="PNG", optimize=True)
    raw_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{raw_b64}"


def resize_keep_aspect(image: np.ndarray, max_dimension: int = 600) -> np.ndarray:
    """Resizes an image maintaining aspect ratio for fast preview or processing."""
    h, w = image.shape[:2]
    if max(h, w) <= max_dimension:
        return image
    scale = max_dimension / float(max(h, w))
    new_w, new_h = max(1, round(w * scale)), max(1, round(h * scale))
    return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
