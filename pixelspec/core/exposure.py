"""
PixelSpec Core Exposure and Dynamic Range Analysis Module
Zonal histogram analysis, highlight burnout, shadow crushing, and Shannon entropy.
"""

from typing import Dict, Any, Tuple
import numpy as np
import cv2


def compute_shannon_entropy(channel: np.ndarray) -> float:
    """Computes Shannon entropy (information richness) of an 8-bit image channel."""
    hist, _ = np.histogram(channel, bins=256, range=(0, 256), density=True)
    # Filter zero probabilities to avoid log(0)
    p = hist[hist > 0]
    return float(-np.sum(p * np.log2(p)))


def evaluate_exposure(
    rgb_image: np.ndarray,
    foreground_mask: np.ndarray = None
) -> Dict[str, Any]:
    """
    Evaluates tonal balance, clipping, dynamic range, and exposure quality.
    """
    gray = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2GRAY)
    
    if foreground_mask is not None and np.count_nonzero(foreground_mask) > 50:
        pixels = gray[foreground_mask.astype(bool)]
    else:
        pixels = gray.ravel()

    # Dynamic Range percentiles
    p5, p50, p95 = np.percentile(pixels, [5, 50, 95])
    dynamic_range = float(p95 - p5)

    # Clipping analysis
    blown_highlights = float(np.mean(pixels >= 252))
    crushed_shadows = float(np.mean(pixels <= 5))

    # Shannon Entropy
    entropy = compute_shannon_entropy(pixels)

    # Zonal Histogram Percentages (Zones: Shadow, Midtone, Highlight)
    shadow_frac = float(np.mean(pixels < 64))
    midtone_frac = float(np.mean((pixels >= 64) & (pixels <= 192)))
    highlight_frac = float(np.mean(pixels > 192))

    # Exposure Score Calculation (100 is ideal balanced exposure)
    # Penalize blown highlights (severe in e-commerce), crushed shadows, or low dynamic range
    penalty_highlights = min(50.0, blown_highlights * 400.0)
    penalty_shadows = min(35.0, crushed_shadows * 250.0)
    
    # Penalize extreme dark or washed out midtones
    luminance_offset = abs(p50 - 135.0)
    penalty_luminance = min(30.0, (luminance_offset / 100.0) * 35.0)

    # Bonus for healthy dynamic range (> 120)
    dr_factor = np.clip(dynamic_range / 160.0, 0.4, 1.0)

    raw_score = 100.0 - (penalty_highlights + penalty_shadows + penalty_luminance)
    final_score = float(np.clip(raw_score * dr_factor, 0.0, 100.0))

    issues = []
    if blown_highlights > 0.08:
        issues.append(f"Highlight clipping detected ({round(blown_highlights * 100, 1)}% overexposed).")
    if crushed_shadows > 0.10:
        issues.append(f"Shadow detail loss detected ({round(crushed_shadows * 100, 1)}% underexposed).")
    if dynamic_range < 90.0:
        issues.append("Low tonal contrast / compressed dynamic range.")

    return {
        "median_luminance": round(float(p50), 1),
        "dynamic_range": round(dynamic_range, 1),
        "highlight_clipping_ratio": round(blown_highlights, 4),
        "shadow_clipping_ratio": round(crushed_shadows, 4),
        "shannon_entropy": round(entropy, 2),
        "zonal_distribution": {
            "shadows": round(shadow_frac * 100, 1),
            "midtones": round(midtone_frac * 100, 1),
            "highlights": round(highlight_frac * 100, 1)
        },
        "exposure_score": round(final_score, 1),
        "issues": issues,
        "is_acceptable": len(issues) == 0 and final_score >= 60.0
    }
