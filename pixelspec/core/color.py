"""
PixelSpec Core Color Analysis Module
CIE-L*a*b* color metrics, Delta E computation, and background purity evaluation.
"""

from typing import Dict, Any, Tuple
import numpy as np
import cv2


def rgb_to_cielab(rgb_image: np.ndarray) -> np.ndarray:
    """Converts uint8 RGB image to CIE-L*a*b* floating-point representation."""
    norm_rgb = rgb_image.astype(np.float32) / 255.0
    return cv2.cvtColor(norm_rgb, cv2.COLOR_RGB2LAB)


def compute_delta_e76(lab1: np.ndarray, lab2: np.ndarray) -> np.ndarray:
    """
    Computes Euclidean Delta E (CIE 1976) between two Lab arrays or a Lab array and reference Lab.
    """
    diff = lab1.astype(np.float32) - lab2.astype(np.float32)
    return np.sqrt(np.sum(diff ** 2, axis=-1))


def analyze_background_color(
    rgb_image: np.ndarray,
    background_mask: np.ndarray,
    target_rgb: Tuple[int, int, int] = (255, 255, 255)
) -> Dict[str, Any]:
    """
    Evaluates background quality against e-commerce white background standards.
    Measures:
    - Delta E from target pure white (L*=100, a*=0, b*=0)
    - Median RGB values in background
    - Background chromatic dispersion (spread/variance in color)
    - Purity score (0 to 100)
    """
    h, w = rgb_image.shape[:2]
    bg_pixels = np.count_nonzero(background_mask)
    total_pixels = h * w
    bg_ratio = float(bg_pixels / max(1, total_pixels))

    if bg_pixels < 50:
        return {
            "bg_pixel_count": int(bg_pixels),
            "bg_coverage_ratio": bg_ratio,
            "mean_rgb": [0.0, 0.0, 0.0],
            "delta_e_from_white": 99.0,
            "dispersion_std": 99.0,
            "purity_score": 0.0,
            "is_pure_white": False,
            "assessment": "Insufficient background pixels identified."
        }

    bg_rgb = rgb_image[background_mask].astype(np.float32)
    mean_rgb = [float(np.mean(bg_rgb[:, 0])), float(np.mean(bg_rgb[:, 1])), float(np.mean(bg_rgb[:, 2]))]
    median_rgb = [float(np.median(bg_rgb[:, 0])), float(np.median(bg_rgb[:, 1])), float(np.median(bg_rgb[:, 2]))]

    lab_img = rgb_to_cielab(rgb_image)
    bg_lab = lab_img[background_mask]

    # Target pure white in Lab: L* = 100, a* = 0, b* = 0
    target_lab = np.array([100.0, 0.0, 0.0], dtype=np.float32)
    delta_es = compute_delta_e76(bg_lab, target_lab)

    p90_delta_e = float(np.percentile(delta_es, 90))
    median_delta_e = float(np.median(delta_es))

    # Dispersion: std deviation of Lab components within background
    dispersion = float(np.mean(np.std(bg_lab, axis=0)))

    # Pure white check: RGB >= 250 in all channels and low Delta E
    is_pure_white = bool(median_rgb[0] >= 248 and median_rgb[1] >= 248 and median_rgb[2] >= 248 and median_delta_e < 8.0)

    # Compute a continuous purity score (100 = seamless studio white, 0 = messy/dark)
    # Delta E of 0 -> 100%, Delta E of 25 -> ~50%, Delta E of 50 -> 0%
    score_from_de = max(0.0, 100.0 - (median_delta_e * 2.2))
    score_from_dispersion = max(0.0, 100.0 - (dispersion * 3.5))
    purity_score = float(np.clip(0.7 * score_from_de + 0.3 * score_from_dispersion, 0.0, 100.0))

    return {
        "bg_pixel_count": int(bg_pixels),
        "bg_coverage_ratio": bg_ratio,
        "mean_rgb": mean_rgb,
        "median_rgb": median_rgb,
        "median_delta_e": round(median_delta_e, 2),
        "p90_delta_e": round(p90_delta_e, 2),
        "dispersion_std": round(dispersion, 2),
        "purity_score": round(purity_score, 1),
        "is_pure_white": is_pure_white,
        "assessment": "Pure white seamless studio" if is_pure_white else (
            "Light neutral background" if purity_score >= 70 else "Non-standard colored or textured background"
        )
    }
