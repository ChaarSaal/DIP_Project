"""
PixelSpec Quality & Compliance Configurations
Defines standard thresholds, weights, and policies for e-commerce image inspection.
"""

from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class QualityThresholds:
    # Resolution limits
    min_width: int = 800
    min_height: int = 800
    recommended_min_dim: int = 1000

    # Sharpness / Blur metrics
    min_tenengrad: float = 85.0          # Spatial gradient energy
    min_laplacian_var: float = 120.0     # Laplacian variance
    min_high_freq_ratio: float = 0.035   # FFT spectral roll-off ratio

    # Noise limits
    max_mad_noise: float = 6.5           # Median Absolute Deviation on wavelets/residuals
    min_snr_db: float = 24.0             # Signal-to-Noise Ratio (dB)

    # Exposure & Dynamic Range
    max_highlight_clipping: float = 0.05 # Fraction of blown out pixels (> 250)
    max_shadow_clipping: float = 0.06    # Fraction of crushed black pixels (< 5)
    min_dynamic_range: float = 130.0     # 95th - 5th percentile intensity spread
    target_mean_luminance: float = 140.0 # Target center for product luminance

    # Background Compliance
    min_bg_purity_score: float = 85.0    # Color uniformity & white balance score
    max_bg_delta_e: float = 12.0         # Max allowable Delta E from target white
    min_bg_coverage: float = 0.15        # Background must occupy at least 15% of frame

    # Framing & Geometry
    min_product_occupancy: float = 0.55  # Product should fill at least 55% of frame
    max_product_occupancy: float = 0.88  # Max 88% to avoid suffocating the frame
    min_margin_ratio: float = 0.05       # Minimum 5% breathing margin on all 4 sides
    max_center_offset: float = 0.15      # Bounding box center distance from image center
    allow_edge_contact: bool = False     # Products must not touch or clip outer boundary


@dataclass
class ComplianceProfile:
    name: str
    description: str
    thresholds: QualityThresholds = field(default_factory=QualityThresholds)
    weights: Dict[str, float] = field(default_factory=lambda: {
        "sharpness": 0.25,
        "exposure": 0.20,
        "noise": 0.15,
        "background": 0.20,
        "framing": 0.20,
    })

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "thresholds": self.thresholds.__dict__,
            "weights": self.weights,
        }


# Default Presets
PROFILES: Dict[str, ComplianceProfile] = {
    "standard": ComplianceProfile(
        name="Standard E-Commerce",
        description="Standard general catalog inspection suitable for mainstream e-commerce listings."
    ),
    "studio_pro": ComplianceProfile(
        name="Studio Pro / Pure White",
        description="Strict guidelines requiring pure seamless background (RGB > 245) and high sharpness.",
        thresholds=QualityThresholds(
            min_width=1200,
            min_height=1200,
            min_tenengrad=110.0,
            min_laplacian_var=160.0,
            max_mad_noise=5.0,
            max_bg_delta_e=8.0,
            min_bg_purity_score=92.0,
            min_product_occupancy=0.65,
            max_product_occupancy=0.85,
            min_margin_ratio=0.06,
        )
    ),
    "relaxed": ComplianceProfile(
        name="Relaxed Marketplace",
        description="Accommodating profile for secondary lifestyle shots or vendor uploads.",
        thresholds=QualityThresholds(
            min_width=600,
            min_height=600,
            min_tenengrad=60.0,
            min_laplacian_var=80.0,
            max_mad_noise=9.0,
            max_bg_delta_e=22.0,
            min_bg_purity_score=70.0,
            min_product_occupancy=0.40,
            max_product_occupancy=0.92,
            min_margin_ratio=0.03,
            allow_edge_contact=True,
        )
    ),
}
