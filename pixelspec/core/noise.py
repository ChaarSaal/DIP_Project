"""
PixelSpec Core Noise Estimation Module
High-frequency residual extraction, Donoho-Johnstone Median Absolute Deviation (MAD) estimator,
and Signal-to-Noise Ratio (SNR) evaluation.
"""

from typing import Dict, Any, Tuple
import numpy as np
import cv2


def estimate_mad_noise(gray: np.ndarray, mask: np.ndarray = None) -> Tuple[float, float, np.ndarray]:
    """
    Estimates additive Gaussian noise standard deviation using MAD on high-pass residuals.
    Method: Donoho & Johnstone robust wavelet/subband estimator.
    Kernel: 3x3 pseudo-Laplacian noise filter:
        [ 1, -2,  1 ]
        [-2,  4, -2 ] / sqrt(36) = / 6.0
        [ 1, -2,  1 ]
    """
    gray_f = gray.astype(np.float32)
    noise_kernel = np.array([
        [1.0, -2.0,  1.0],
        [-2.0,  4.0, -2.0],
        [1.0, -2.0,  1.0]
    ], dtype=np.float32) / 6.0

    residuals = cv2.filter2D(gray_f, -1, noise_kernel)
    abs_res = np.abs(residuals)

    # To avoid confusing sharp product edges with noise, find homogeneous/smooth regions
    grad = cv2.magnitude(
        cv2.Sobel(gray_f, cv2.CV_32F, 1, 0),
        cv2.Sobel(gray_f, cv2.CV_32F, 0, 1)
    )

    if mask is not None and np.count_nonzero(mask) > 100:
        smooth_mask = (grad < np.percentile(grad[mask], 45)) & mask.astype(bool)
    else:
        smooth_mask = grad < np.percentile(grad, 45)

    if np.count_nonzero(smooth_mask) > 64:
        flat_residuals = residuals[smooth_mask]
        median_val = np.median(flat_residuals)
        mad = float(np.median(np.abs(flat_residuals - median_val)))
        sigma_est = mad / 0.6744897501960817  # Normal distribution scaling factor
        mean_signal = float(np.mean(gray_f[smooth_mask]))
    else:
        sigma_est = float(np.std(residuals))
        mean_signal = float(np.mean(gray_f))

    # Signal-to-noise ratio in decibels (dB)
    snr_db = float(20.0 * np.log10(max(1.0, mean_signal) / max(1e-4, sigma_est)))

    # Noise heatmap visualization
    noise_viz = np.clip((abs_res / max(1e-4, sigma_est * 3.0)) * 255.0, 0, 255).astype(np.uint8)

    return sigma_est, snr_db, noise_viz


def evaluate_noise(
    rgb_image: np.ndarray,
    foreground_mask: np.ndarray = None
) -> Dict[str, Any]:
    """
    Evaluates noise graininess and clean visual clarity.
    Returns metrics, score out of 100, and residual noise map.
    """
    gray = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2GRAY)
    sigma, snr_db, noise_map = estimate_mad_noise(gray, foreground_mask)

    # Scoring:
    # sigma < 2.5: pristine studio quality (score 95-100)
    # sigma ~ 5.0: acceptable consumer photo (score ~80)
    # sigma > 12.0: noticeable grain/sensor noise (score < 50)
    score = np.clip(100.0 - (sigma * 5.5), 0.0, 100.0)

    if sigma <= 4.0:
        verdict = "Clean / Low Graininess"
    elif sigma <= 8.0:
        verdict = "Moderate Grain / Acceptable"
    else:
        verdict = "Significant Grain / High Noise"

    return {
        "estimated_noise_sigma": round(sigma, 2),
        "snr_db": round(snr_db, 1),
        "noise_score": round(float(score), 1),
        "verdict": verdict,
        "noise_map": noise_map,
        "is_clean": sigma <= 7.0
    }
