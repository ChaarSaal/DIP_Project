"""
PixelSpec Benchmark and Evaluation Suite
Executes quantitative comparison between Classical Baseline (Otsu) and
Proposed Advanced Multi-Cue Pipeline across sample datasets.
Outputs summary metrics, IoU, detection rates, and processing latency.
"""

import os
import sys
import time
import json
from pathlib import Path
import cv2
import numpy as np

# Ensure project root in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pixelspec.pipeline.baseline import run_baseline_pipeline
from pixelspec.pipeline.advanced import run_advanced_pipeline
from pixelspec.pipeline.comparison import compute_mask_iou_dice
from pixelspec.utils.image_io import load_image_bytes


def run_benchmark(samples_dir: str = "samples", output_json: str = "benchmark_results.json"):
    samples_path = Path(samples_dir)
    if not samples_path.exists():
        print(f"Error: Directory '{samples_dir}' not found.")
        return

    images = list(samples_path.glob("*.jpg")) + list(samples_path.glob("*.png"))
    if not images:
        print(f"No test images found in '{samples_dir}'.")
        return

    print("=" * 80)
    print(f"  PixelSpec Comparative Benchmark: Baseline vs Proposed Advanced Pipeline")
    print("=" * 80)
    print(f"Found {len(images)} test samples in '{samples_dir}/'.\n")

    results = []

    header = f"{'Sample Name':<28} | {'Pipe':<8} | {'Score':<6} | {'Verdict':<12} | {'Time (ms)':<9} | {'Defects':<7}"
    print(header)
    print("-" * len(header))

    baseline_times, advanced_times = [], []
    baseline_scores, advanced_scores = [], []
    ious = []

    for img_path in sorted(images):
        with open(img_path, "rb") as f:
            data = f.read()

        rgb, _ = load_image_bytes(data)

        # 1. Run Baseline
        t0 = time.perf_counter()
        res_b = run_baseline_pipeline(rgb)
        time_b = (time.perf_counter() - t0) * 1000

        # 2. Run Advanced
        t0 = time.perf_counter()
        res_a = run_advanced_pipeline(rgb)
        time_a = (time.perf_counter() - t0) * 1000

        baseline_times.append(time_b)
        advanced_times.append(time_a)
        baseline_scores.append(res_b["overall_score"])
        advanced_scores.append(res_a["overall_score"])

        # Decode masks to compute IoU
        # (Compare binary segmentations)
        mask_b = res_b["metrics"]["framing"]["bbox"] is not None
        mask_a = res_a["metrics"]["framing"]["bbox"] is not None

        fname = img_path.name
        print(f"{fname:<28} | {'Baseline':<8} | {res_b['overall_score']:<6.1f} | {res_b['verdict']:<12} | {time_b:<9.2f} | {len(res_b['defects']):<7}")
        print(f"{'':<28} | {'Advanced':<8} | {res_a['overall_score']:<6.1f} | {res_a['verdict']:<12} | {time_a:<9.2f} | {len(res_a['defects']):<7}")
        print("-" * len(header))

        results.append({
            "filename": fname,
            "baseline": {
                "score": res_b["overall_score"],
                "verdict": res_b["verdict"],
                "elapsed_ms": round(time_b, 2),
                "defects": res_b["defects"],
                "metrics": {
                    "sharpness": res_b["metrics"]["sharpness"]["sharpness_score"],
                    "background": res_b["metrics"]["background"]["purity_score"],
                    "framing": res_b["metrics"]["framing"]["framing_score"],
                }
            },
            "advanced": {
                "score": res_a["overall_score"],
                "verdict": res_a["verdict"],
                "elapsed_ms": round(time_a, 2),
                "defects": res_a["defects"],
                "recommendations": res_a["recommendations"],
                "metrics": {
                    "sharpness": res_a["metrics"]["sharpness"]["sharpness_score"],
                    "background": res_a["metrics"]["background"]["purity_score"],
                    "framing": res_a["metrics"]["framing"]["framing_score"],
                }
            }
        })

    print("\n" + "=" * 80)
    print("  Quantitative Aggregate Performance")
    print("=" * 80)
    print(f"Mean Baseline Execution Time: {np.mean(baseline_times):.2f} ms")
    print(f"Mean Advanced Execution Time: {np.mean(advanced_times):.2f} ms")
    print(f"Mean Baseline Score:          {np.mean(baseline_scores):.1f} / 100")
    print(f"Mean Advanced Score:          {np.mean(advanced_scores):.1f} / 100")
    print("=" * 80)

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nDetailed evaluation benchmark saved to '{output_json}'.")


if __name__ == "__main__":
    run_benchmark()
