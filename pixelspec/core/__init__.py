"""
PixelSpec Core DIP Algorithms
Color, Sharpness, Exposure, Noise, Geometry, and Segmentation.
"""

from pixelspec.core.color import analyze_background_color, rgb_to_cielab, compute_delta_e76
from pixelspec.core.sharpness import evaluate_sharpness, compute_spatial_sharpness, compute_fft_spectral_ratio
from pixelspec.core.exposure import evaluate_exposure, compute_shannon_entropy
from pixelspec.core.noise import evaluate_noise, estimate_mad_noise
from pixelspec.core.geometry import analyze_product_framing
from pixelspec.core.segmentation import (
    segment_baseline_otsu,
    segment_advanced_multicue,
    SegmentationResult
)
