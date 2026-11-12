"""
PixelSpec Advanced Inspection Pipeline
The proposed multi-cue DIP framework combining Bilateral edge-preservation,
CIELAB Delta E segmentation, GrabCut refinement, and dual-domain quality audit.
"""

import time
from typing import Dict, Any, Optional, List
import numpy as np
import cv2

from pixelspec.config import ComplianceProfile, PROFILES
from pixelspec.core.segmentation import segment_advanced_multicue
from pixelspec.core.sharpness import evaluate_sharpness
from pixelspec.core.exposure import evaluate_exposure
from pixelspec.core.noise import evaluate_noise
from pixelspec.core.color import analyze_background_color
from pixelspec.core.geometry import analyze_product_framing
from pixelspec.utils.image_io import image_to_base64_png


def generate_actionable_recommendations(
    defects: List[str],
    metrics: Dict[str, Any]
) -> List[str]:
    """Generates seller-friendly, prioritized instructions to fix detected flaws."""
    recs = []

    # 1. Background advice
    bg = metrics["background"]
    if not bg["is_pure_white"] and bg["purity_score"] < 80.0:
        if bg["median_delta_e"] > 15.0:
            recs.append("Background: Re-shoot against a seamless pure white sweep (RGB 255) or boost background backlight exposure.")
        else:
            recs.append("Background: Slightly increase background exposure or adjust white balance to eliminate subtle color cast.")

    # 2. Framing advice
    framing = metrics["framing"]
    if framing.get("is_edge_clipped"):
        recs.append("Framing: Pull camera back or widen zoom. The product is touching or clipped by the image edge.")
    elif framing.get("linear_coverage", 0) < 0.60:
        recs.append("Framing: Crop tighter around the product. It currently occupies less than 60% of the vertical/horizontal frame.")
    elif framing.get("center_offset", 0) > 0.12:
        recs.append("Framing: Center the product horizontally and vertically within the canvas.")

    # 3. Focus / Sharpness advice
    sharpness = metrics["sharpness"]
    if sharpness["sharpness_score"] < 60.0:
        recs.append("Focus: Image appears soft or blurred. Use a tripod, narrow aperture (f/8-f/11), and verify focus on the main product logo/texture.")

    # 4. Exposure advice
    exposure = metrics["exposure"]
    if exposure["highlight_clipping_ratio"] > 0.05:
        recs.append("Lighting: Highlights are blown out with lost surface detail. Reduce key light power or use a diffuser.")
    elif exposure["shadow_clipping_ratio"] > 0.08:
        recs.append("Lighting: Dark shadow zones lack detail. Add a bounce card or fill light to lift the dark areas.")

    # 5. Noise advice
    noise = metrics["noise"]
    if not noise["is_clean"]:
        recs.append(f"Sensor Grain: Noticeable grain detected (sigma={noise['estimated_noise_sigma']}). Lower camera ISO to 100 or 200.")

    if not recs:
        recs.append("Your photograph meets high e-commerce catalog standards. Ready for publication!")

    return recs[:3]


def run_advanced_pipeline(
    rgb_image: np.ndarray,
    profile: Optional[ComplianceProfile] = None
) -> Dict[str, Any]:
    """
    Executes the advanced multi-cue DIP pipeline on the input RGB image.
    """
    start_time = time.perf_counter()
    if profile is None:
        profile = PROFILES["standard"]

    h, w = rgb_image.shape[:2]

    # 1. Advanced Multi-Cue Segmentation
    seg_res = segment_advanced_multicue(rgb_image)
    fg_mask = seg_res.mask
    bg_mask = ~fg_mask

    # To ensure metrics within product are not polluted by boundary transition pixels,
    # erode the product mask slightly for interior evaluation
    kernel3 = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    interior_mask = cv2.erode(fg_mask.astype(np.uint8), kernel3).astype(bool) if fg_mask.any() else fg_mask

    # 2. Comprehensive Metric Evaluations
    sharpness_res = evaluate_sharpness(rgb_image, interior_mask)
    exposure_res = evaluate_exposure(rgb_image, interior_mask)
    noise_res = evaluate_noise(rgb_image, interior_mask)
    bg_res = analyze_background_color(rgb_image, bg_mask)
    framing_res = analyze_product_framing(fg_mask, (h, w))

    # 3. Multi-factor Weighted Scoring
    weights = profile.weights
    overall_score = (
        weights["sharpness"] * sharpness_res["sharpness_score"] +
        weights["exposure"] * exposure_res["exposure_score"] +
        weights["noise"] * noise_res["noise_score"] +
        weights["background"] * bg_res["purity_score"] +
        weights["framing"] * framing_res["framing_score"]
    )
    overall_score = round(float(np.clip(overall_score, 0.0, 100.0)), 1)

    # 4. Defect Compilation
    defects = []
    if sharpness_res["sharpness_score"] < 58.0:
        defects.append(f"Blur / Low product sharpness (Score: {sharpness_res['sharpness_score']}/100).")
    defects.extend(exposure_res["issues"])
    if not noise_res["is_clean"]:
        defects.append(f"High grain / sensor noise (sigma={noise_res['estimated_noise_sigma']}).")
    if bg_res["purity_score"] < 78.0:
        defects.append(f"Non-compliant background (Delta E: {bg_res['median_delta_e']}, Purity: {bg_res['purity_score']}/100).")
    defects.extend(framing_res["defects"])

    # Verdict
    if overall_score >= 80.0 and len(defects) == 0:
        verdict = "PASS"
    elif overall_score >= 58.0 and not framing_res.get("is_edge_clipped", False):
        verdict = "NEEDS_IMPROVEMENT"
    else:
        verdict = "FAIL"

    # Actionable guidance
    metrics_summary = {
        "sharpness": sharpness_res,
        "exposure": exposure_res,
        "noise": noise_res,
        "background": bg_res,
        "framing": framing_res,
    }
    recommendations = generate_actionable_recommendations(defects, metrics_summary)

    # 5. Visual Annotated Overlay
    annotated = rgb_image.copy()
    if framing_res["bbox"]:
        x, y, bw, bh = framing_res["bbox"]
        box_color = (30, 200, 30) if verdict == "PASS" else ((240, 150, 0) if verdict == "NEEDS_IMPROVEMENT" else (230, 40, 40))
        # Draw bounding box
        cv2.rectangle(annotated, (x, y), (x + bw, y + bh), box_color, 2)
        # Margin guide lines
        cv2.line(annotated, (x, 0), (x, h), (180, 180, 180), 1, cv2.LINE_AA)
        cv2.line(annotated, (x + bw, 0), (x + bw, h), (180, 180, 180), 1, cv2.LINE_AA)
        cv2.line(annotated, (0, y), (w, y), (180, 180, 180), 1, cv2.LINE_AA)
        cv2.line(annotated, (0, y + bh), (w, y + bh), (180, 180, 180), 1, cv2.LINE_AA)

        # Label pill
        cv2.putText(annotated, f"Coverage: {round(framing_res['linear_coverage']*100)}%", (x + 5, max(24, y - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, box_color, 2)

    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

    # Convert stage maps to base64 for UI
    stage_b64 = {}
    for name, img_array in seg_res.stages.items():
        stage_b64[name] = image_to_base64_png(img_array)
    stage_b64["annotated"] = image_to_base64_png(annotated)
    stage_b64["edge_heatmap"] = image_to_base64_png(sharpness_res["edge_map"])
    stage_b64["fft_spectrum"] = image_to_base64_png(sharpness_res["fft_spectrum_viz"])
    stage_b64["noise_residual_map"] = image_to_base64_png(noise_res["noise_map"])

    return {
        "pipeline_name": "Proposed Advanced Multi-Cue Pipeline",
        "elapsed_ms": elapsed_ms,
        "overall_score": overall_score,
        "verdict": verdict,
        "defects": defects,
        "recommendations": recommendations,
        "metrics": metrics_summary,
        "segmentation_confidence": seg_res.confidence,
        "stage_images": stage_b64,
    }
