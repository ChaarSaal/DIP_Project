"""
PixelSpec Baseline Inspection Pipeline
Classical DIP implementation using traditional Otsu thresholding and standard metrics.
Required by DIP Course Guidelines for baseline-vs-proposed comparative study.
"""

import time
from typing import Dict, Any, Optional
import numpy as np
import cv2

from pixelspec.config import ComplianceProfile, PROFILES
from pixelspec.core.segmentation import segment_baseline_otsu
from pixelspec.core.sharpness import evaluate_sharpness
from pixelspec.core.exposure import evaluate_exposure
from pixelspec.core.noise import evaluate_noise
from pixelspec.core.color import analyze_background_color
from pixelspec.core.geometry import analyze_product_framing
from pixelspec.utils.image_io import image_to_base64_png


def run_baseline_pipeline(
    rgb_image: np.ndarray,
    profile: Optional[ComplianceProfile] = None
) -> Dict[str, Any]:
    """
    Executes the classical baseline pipeline on the input RGB image.
    """
    start_time = time.perf_counter()
    if profile is None:
        profile = PROFILES["standard"]

    h, w = rgb_image.shape[:2]

    # 1. Classical Segmentation (Otsu)
    seg_res = segment_baseline_otsu(rgb_image)
    fg_mask = seg_res.mask
    bg_mask = ~fg_mask

    # 2. Metric Evaluations
    sharpness_res = evaluate_sharpness(rgb_image, fg_mask)
    exposure_res = evaluate_exposure(rgb_image, fg_mask)
    noise_res = evaluate_noise(rgb_image, fg_mask)
    bg_res = analyze_background_color(rgb_image, bg_mask)
    framing_res = analyze_product_framing(fg_mask, (h, w))

    # 3. Overall Scoring using Baseline weights
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
    if sharpness_res["sharpness_score"] < 55.0:
        defects.append("Blur / Insufficient product sharpness.")
    defects.extend(exposure_res["issues"])
    if not noise_res["is_clean"]:
        defects.append(f"Excessive grain / noise (sigma={noise_res['estimated_noise_sigma']}).")
    if bg_res["purity_score"] < 75.0:
        defects.append("Background is not uniform / off-white.")
    defects.extend(framing_res["defects"])

    # Verdict
    if overall_score >= 82.0 and not defects:
        verdict = "PASS"
    elif overall_score >= 60.0:
        verdict = "NEEDS_IMPROVEMENT"
    else:
        verdict = "FAIL"

    # 5. Visual Annotated Overlay
    annotated = rgb_image.copy()
    if framing_res["bbox"]:
        x, y, bw, bh = framing_res["bbox"]
        # Draw bounding box
        box_color = (0, 200, 0) if verdict == "PASS" else ((220, 140, 0) if verdict == "NEEDS_IMPROVEMENT" else (220, 20, 20))
        cv2.rectangle(annotated, (x, y), (x + bw, y + bh), box_color, 2)
        cv2.putText(annotated, f"Product {round(framing_res['linear_coverage']*100)}%", (x, max(25, y - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, box_color, 2)

    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

    # Convert stage maps to base64
    stage_b64 = {}
    for name, img_array in seg_res.stages.items():
        stage_b64[name] = image_to_base64_png(img_array)
    stage_b64["annotated"] = image_to_base64_png(annotated)
    stage_b64["edge_map"] = image_to_base64_png(sharpness_res["edge_map"])

    return {
        "pipeline_name": "Baseline (Otsu + Classical DIP)",
        "elapsed_ms": elapsed_ms,
        "overall_score": overall_score,
        "verdict": verdict,
        "defects": defects,
        "metrics": {
            "sharpness": sharpness_res,
            "exposure": exposure_res,
            "noise": noise_res,
            "background": bg_res,
            "framing": framing_res,
        },
        "segmentation_confidence": seg_res.confidence,
        "stage_images": stage_b64,
    }
