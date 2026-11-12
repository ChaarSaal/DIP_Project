"""
PixelSpec Sample Data Generator
Generates realistic synthetic e-commerce product test images representing various
compliance conditions (Pass, Blurry, High Noise, Edge Clipped, Poor Background, Overexposed).
"""

import os
import cv2
import numpy as np


def create_product_graphic(w: int = 1000, h: int = 1000) -> np.ndarray:
    """Renders a synthetic high-contrast product (smart gadget) on pure white."""
    canvas = np.full((h, w, 3), 255, dtype=np.uint8)

    # Main gadget body (rounded rectangle/pill)
    cx, cy = w // 2, h // 2
    bw, bh = int(w * 0.40), int(h * 0.55)
    x1, y1 = cx - bw // 2, cy - bh // 2
    x2, y2 = cx + bw // 2, cy + bh // 2

    # Draw gadget chassis
    cv2.rectangle(canvas, (x1, y1), (x2, y2), (35, 45, 60), -1)
    # Inner display screen
    sx1, sy1 = x1 + 25, y1 + 35
    sx2, sy2 = x2 - 25, y2 - 120
    cv2.rectangle(canvas, (sx1, sy1), (sx2, sy2), (15, 20, 28), -1)

    # Detailed UI lines on screen (provides high-frequency texture)
    for i in range(sy1 + 30, sy2 - 20, 24):
        cv2.line(canvas, (sx1 + 20, i), (sx2 - 20, i), (60, 180, 240), 2)

    # Brand text / logo
    cv2.putText(canvas, "PIXELSPEC", (cx - 70, y2 - 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (220, 220, 220), 2)
    # Control button
    cv2.circle(canvas, (cx, y2 - 30), 16, (80, 95, 115), -1)

    return canvas


def generate_samples(output_dir: str = "samples"):
    os.makedirs(output_dir, exist_ok=True)
    base_clean = create_product_graphic(1000, 1000)

    # 1. Standard Pass Studio Image
    path_pass = os.path.join(output_dir, "sample_pass_studio.jpg")
    cv2.imwrite(path_pass, cv2.cvtColor(base_clean, cv2.COLOR_RGB2BGR), [int(cv2.IMWRITE_JPEG_QUALITY), 95])
    print(f"Generated: {path_pass}")

    # 2. Defect: Deficient Sharpness / Out of focus (Gaussian blur)
    blurry = cv2.GaussianBlur(base_clean, (25, 25), 8.0)
    path_blur = os.path.join(output_dir, "sample_fail_blurry.jpg")
    cv2.imwrite(path_blur, cv2.cvtColor(blurry, cv2.COLOR_RGB2BGR), [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    print(f"Generated: {path_blur}")

    # 3. Defect: High Sensor Noise (Simulating high ISO sensor grain)
    noise = np.random.normal(0, 22, base_clean.shape).astype(np.float32)
    noisy = np.clip(base_clean.astype(np.float32) + noise, 0, 255).astype(np.uint8)
    path_noise = os.path.join(output_dir, "sample_fail_noisy.jpg")
    cv2.imwrite(path_noise, cv2.cvtColor(noisy, cv2.COLOR_RGB2BGR), [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    print(f"Generated: {path_noise}")

    # 4. Defect: Edge-Clipped & Off-Center
    clipped_canvas = np.full((1000, 1000, 3), 255, dtype=np.uint8)
    # Paste base shifted strongly to the right edge so it touches border
    clipped_canvas[:, 250:] = base_clean[:, :750]
    path_clipped = os.path.join(output_dir, "sample_fail_clipped.jpg")
    cv2.imwrite(path_clipped, cv2.cvtColor(clipped_canvas, cv2.COLOR_RGB2BGR), [int(cv2.IMWRITE_JPEG_QUALITY), 95])
    print(f"Generated: {path_clipped}")

    # 5. Defect: Non-Uniform / Yellowish Background
    bad_bg_canvas = base_clean.copy()
    bg_mask = (bad_bg_canvas[:, :, 0] > 240) & (bad_bg_canvas[:, :, 1] > 240) & (bad_bg_canvas[:, :, 2] > 240)
    # Tint background to a yellowish-gray color with a gradient
    y_coords, _ = np.mgrid[0:1000, 0:1000]
    tint_b = np.clip(160 + (y_coords // 15), 0, 220).astype(np.uint8)
    tint_g = np.clip(200 + (y_coords // 20), 0, 235).astype(np.uint8)
    tint_r = np.clip(215 + (y_coords // 25), 0, 245).astype(np.uint8)

    bad_bg_canvas[bg_mask, 0] = tint_r[bg_mask]
    bad_bg_canvas[bg_mask, 1] = tint_g[bg_mask]
    bad_bg_canvas[bg_mask, 2] = tint_b[bg_mask]
    path_bg = os.path.join(output_dir, "sample_fail_bad_bg.jpg")
    cv2.imwrite(path_bg, cv2.cvtColor(bad_bg_canvas, cv2.COLOR_RGB2BGR), [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    print(f"Generated: {path_bg}")

    # 6. Defect: Overexposed / Blown Out (product body is severely overexposed/clipped)
    overexposed = np.clip(base_clean.astype(np.float32) + 210, 0, 255).astype(np.uint8)
    path_over = os.path.join(output_dir, "sample_fail_overexposed.jpg")
    cv2.imwrite(path_over, cv2.cvtColor(overexposed, cv2.COLOR_RGB2BGR), [int(cv2.IMWRITE_JPEG_QUALITY), 95])
    print(f"Generated: {path_over}")

    print("\nAll 6 test samples successfully generated in 'samples/' directory.")


if __name__ == "__main__":
    generate_samples()
