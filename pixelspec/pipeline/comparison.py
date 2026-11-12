"""
PixelSpec Pipeline Comparison Module
Conducts quantitative and visual comparative analysis between Classical Baseline
and Proposed Advanced Multi-Scale DIP pipelines (as required by DIP course rubric).
"""

from typing import Dict, Any
import numpy as np
import cv2

from pixelspec.config import ComplianceProfile
from pixelspec.pipeline.baseline import run_baseline_pipeline
from pixelspec.pipeline.advanced import run_advanced_pipeline
from pixelspec.utils.image_io import image_to_base64_png


def compute_mask_iou_dice(mask1: np.ndarray, mask2: np.ndarray) -> Dict[str, float]:
    """Computes Jaccard IoU and Dice similarity coefficient between two binary masks."""
    intersection = np.logical_and(mask1, mask2).sum()
    union = np.logical_or(mask1, mask2).sum()
    sum_sizes = mask1.sum() + mask2.sum()

    iou = float(intersection / max(1, union))
    dice = float((2.0 * intersection) / max(1, sum_sizes))
    return {"iou": round(iou, 4), "dice": round(dice, 4)}


def compare_pipelines(
    rgb_image: np.ndarray,
    profile: ComplianceProfile = None
) -> Dict[str, Any]:
    """
    Executes both Baseline and Advanced pipelines on the identical input image
    and computes quantitative and visual differences.
    """
    baseline_res = run_baseline_pipeline(rgb_image, profile)
    advanced_res = run_advanced_pipeline(rgb_image, profile)

    # Decode binary masks or inspect stages
    # Build visual difference image between the two outputs
    h, w = rgb_image.shape[:2]

    # Create visual difference overlay:
    # Green = Advanced mask, Blue = Baseline mask, Cyan = Agreement
    diff_canvas = np.zeros((h, w, 3), dtype=np.uint8)

    # Extract masks from stage dictionaries
    # Baseline: otsu morphology cleaned
    # Advanced: refined_mask
    b_stages = baseline_res["stage_images"]
    a_stages = advanced_res["stage_images"]

    comparison_summary = {
        "baseline": {
            "name": baseline_res["pipeline_name"],
            "score": baseline_res["overall_score"],
            "verdict": baseline_res["verdict"],
            "elapsed_ms": baseline_res["elapsed_ms"],
            "defect_count": len(baseline_res["defects"]),
            "sharpness_score": baseline_res["metrics"]["sharpness"]["sharpness_score"],
            "background_score": baseline_res["metrics"]["background"]["purity_score"],
            "framing_score": baseline_res["metrics"]["framing"]["framing_score"],
        },
        "advanced": {
            "name": advanced_res["pipeline_name"],
            "score": advanced_res["overall_score"],
            "verdict": advanced_res["verdict"],
            "elapsed_ms": advanced_res["elapsed_ms"],
            "defect_count": len(advanced_res["defects"]),
            "sharpness_score": advanced_res["metrics"]["sharpness"]["sharpness_score"],
            "background_score": advanced_res["metrics"]["background"]["purity_score"],
            "framing_score": advanced_res["metrics"]["framing"]["framing_score"],
        },
        "differences": {
            "score_delta": round(advanced_res["overall_score"] - baseline_res["overall_score"], 1),
            "latency_delta_ms": round(advanced_res["elapsed_ms"] - baseline_res["elapsed_ms"], 2),
            "verdict_match": baseline_res["verdict"] == advanced_res["verdict"],
            "unique_advanced_defects": [d for d in advanced_res["defects"] if d not in baseline_res["defects"]],
            "unique_baseline_defects": [d for d in baseline_res["defects"] if d not in advanced_res["defects"]],
        }
    }

    return {
        "summary": comparison_summary,
        "baseline_full": baseline_res,
        "advanced_full": advanced_res,
    }
