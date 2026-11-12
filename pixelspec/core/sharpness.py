"""
PixelSpec Core Sharpness and Blur Analysis Module
Dual-domain blur detection: Spatial (Tenengrad Sobel + Modified Laplacian) and
Frequency Domain (2D FFT High-Frequency Energy Ratio).
"""

from typing import Dict, Any, Tuple
import numpy as np
import cv2


def compute_spatial_sharpness(gray: np.ndarray, mask: np.ndarray = None) -> Tuple[float, float, np.ndarray]:
    """
    Computes spatial blur/sharpness metrics on a grayscale image.
    Returns:
    - tenengrad_val: Mean squared gradient (Sobel magnitude squared).
    - laplacian_var: Variance of Laplacian operator response.
    - edge_map: Normalized 0-255 visualization of local gradient intensity.
    """
    # 1. Sobel Gradient Magnitude (Tenengrad Criterion)
    gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    sobel_mag_sq = gx ** 2 + gy ** 2

    # 2. Laplacian operator
    lap = cv2.Laplacian(gray, cv2.CV_64F, ksize=3)

    if mask is not None and np.count_nonzero(mask) > 50:
        valid_indices = mask.astype(bool)
        tenengrad = float(np.mean(sobel_mag_sq[valid_indices]))
        laplacian_var = float(np.var(lap[valid_indices]))
    else:
        tenengrad = float(np.mean(sobel_mag_sq))
        laplacian_var = float(np.var(lap))

    # Normalized gradient map for UI visualization
    norm_grad = np.sqrt(sobel_mag_sq)
    p98 = np.percentile(norm_grad, 98) if norm_grad.size > 0 else 1.0
    scaled = np.clip((norm_grad / max(1e-4, p98)) * 255.0, 0, 255).astype(np.uint8)

    return tenengrad, laplacian_var, scaled


def compute_fft_spectral_ratio(gray: np.ndarray, high_freq_threshold: float = 0.15) -> Tuple[float, np.ndarray]:
    """
    Analyzes frequency spectrum using 2D FFT.
    Measures the ratio of high-frequency power to total spectral power.
    Returns:
    - high_freq_ratio: float in range [0, 1]
    - log_spectrum_viz: 0-255 uint8 image of the shifted 2D power spectrum.
    """
    h, w = gray.shape[:2]
    # Perform 2D Fast Fourier Transform
    f_transform = np.fft.fft2(gray.astype(np.float64))
    f_shift = np.fft.fftshift(f_transform)
    magnitude_spectrum = np.abs(f_shift)

    # Compute high-pass mask (distance from DC center)
    center_y, center_x = h // 2, w // 2
    y_coords, x_coords = np.ogrid[:h, :w]
    dist_from_center = np.sqrt((x_coords - center_x) ** 2 + (y_coords - center_y) ** 2)
    max_radius = np.sqrt(center_x ** 2 + center_y ** 2)
    normalized_dist = dist_from_center / max(1e-5, max_radius)

    # High frequency energy vs Total energy (excluding DC component at center)
    ac_mask = normalized_dist > 0.01
    high_mask = normalized_dist >= high_freq_threshold

    total_ac_energy = np.sum(magnitude_spectrum[ac_mask] ** 2)
    high_energy = np.sum(magnitude_spectrum[high_mask] ** 2)

    ratio = float(high_energy / max(1e-8, total_ac_energy))

    # Log spectrum visualization
    log_spectrum = np.log1p(magnitude_spectrum)
    spec_min, spec_max = np.min(log_spectrum), np.max(log_spectrum)
    spec_viz = ((log_spectrum - spec_min) / max(1e-5, spec_max - spec_min) * 255.0).astype(np.uint8)

    return ratio, spec_viz


def evaluate_sharpness(
    rgb_image: np.ndarray,
    foreground_mask: np.ndarray = None
) -> Dict[str, Any]:
    """
    Comprehensive sharpness evaluator.
    Returns metrics, score out of 100, verdict, and visual feature maps.
    """
    gray = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2GRAY)
    tenengrad, lap_var, edge_map = compute_spatial_sharpness(gray, foreground_mask)
    fft_ratio, fft_viz = compute_fft_spectral_ratio(gray)

    # Quality score mapping:
    # Tenengrad: 40 (very blurry) -> 150+ (pin sharp)
    score_tenengrad = np.clip((tenengrad - 30.0) / 1.1, 0, 100)
    # Laplacian: 60 (blurry) -> 200+ (crisp)
    score_laplacian = np.clip((lap_var - 40.0) / 1.5, 0, 100)
    # FFT: 0.015 (soft) -> 0.06+ (textured)
    score_fft = np.clip((fft_ratio - 0.01) / 0.0006, 0, 100)

    composite_score = float(0.45 * score_tenengrad + 0.35 * score_laplacian + 0.20 * score_fft)

    if composite_score >= 75.0:
        verdict = "Sharp & High Focus"
    elif composite_score >= 50.0:
        verdict = "Moderate Focus / Acceptable"
    else:
        verdict = "Deficient Sharpness / Blur Detected"

    return {
        "tenengrad_gradient": round(tenengrad, 2),
        "laplacian_variance": round(lap_var, 2),
        "fft_high_freq_ratio": round(fft_ratio, 5),
        "sharpness_score": round(composite_score, 1),
        "verdict": verdict,
        "edge_map": edge_map,
        "fft_spectrum_viz": fft_viz,
    }
