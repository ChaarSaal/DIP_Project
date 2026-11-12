"""
PixelSpec Core Framing and Geometry Analysis Module
Product occupancy ratio, whitespace margins, centering index, aspect ratio,
and edge-clipping hazard inspection.
"""

from typing import Dict, Any, List, Tuple
import numpy as np
import cv2


def analyze_product_framing(
    mask: np.ndarray,
    image_shape: Tuple[int, int]
) -> Dict[str, Any]:
    """
    Computes geometric compliance metrics from the product segmentation mask:
    - Bounding Box (x, y, w, h)
    - Occupancy ratio (bbox area vs frame, product pixels vs frame)
    - Margins on Top, Bottom, Left, Right
    - Center deviation from image optical center
    - Edge clipping flags (border contact pixels)
    """
    img_h, img_w = image_shape[:2]
    total_area = float(img_h * img_w)

    if not mask.any():
        return {
            "has_product": False,
            "occupancy_ratio": 0.0,
            "bbox": None,
            "margins": {"top": 0.0, "bottom": 0.0, "left": 0.0, "right": 0.0},
            "center_offset": 1.0,
            "is_edge_clipped": False,
            "framing_score": 0.0,
            "defects": ["No product detected in image."]
        }

    # Connected components to isolate main product vs extraneous debris
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
    
    # Filter out tiny noise components (< 0.5% of image area)
    min_comp_area = max(20, int(total_area * 0.005))
    valid_labels = [i for i in range(1, num_labels) if stats[i, cv2.CC_STAT_AREA] >= min_comp_area]

    if not valid_labels:
        # Fallback to entire mask
        cleaned_mask = mask
    else:
        cleaned_mask = np.isin(labels, valid_labels)

    # Find bounding box of all valid components
    y_indices, x_indices = np.where(cleaned_mask)
    x_min, x_max = int(np.min(x_indices)), int(np.max(x_indices))
    y_min, y_max = int(np.min(y_indices)), int(np.max(y_indices))

    bbox_w = x_max - x_min + 1
    bbox_h = y_max - y_min + 1
    bbox = [x_min, y_min, bbox_w, bbox_h]

    # Margin percentages relative to image dimensions
    margin_top = float(y_min / img_h)
    margin_bottom = float((img_h - 1 - y_max) / img_h)
    margin_left = float(x_min / img_w)
    margin_right = float((img_w - 1 - x_max) / img_w)
    min_margin = min(margin_top, margin_bottom, margin_left, margin_right)

    # Coverage / Occupancy: fraction of frame taken by the product bounding box
    bbox_occupancy = float((bbox_w * bbox_h) / total_area)
    pixel_occupancy = float(np.count_nonzero(cleaned_mask) / total_area)
    
    # Linear coverage (largest dimension relative to frame)
    linear_coverage = max(bbox_w / img_w, bbox_h / img_h)

    # Centering offset (Euclidean distance between bbox center and image center, normalized)
    center_x = (x_min + bbox_w / 2.0) / img_w
    center_y = (y_min + bbox_h / 2.0) / img_h
    center_offset = float(np.sqrt((center_x - 0.5) ** 2 + (center_y - 0.5) ** 2))

    # Border clipping check: check if mask touches outer boundary pixels
    top_touch = np.count_nonzero(cleaned_mask[0, :])
    bottom_touch = np.count_nonzero(cleaned_mask[-1, :])
    left_touch = np.count_nonzero(cleaned_mask[:, 0])
    right_touch = np.count_nonzero(cleaned_mask[:, -1])
    total_edge_touch = int(top_touch + bottom_touch + left_touch + right_touch)
    is_edge_clipped = total_edge_touch > 0

    # Framing Score (100 is ideal e-commerce framing)
    defects = []
    framing_score = 100.0

    # Amazon/Shopify recommendation: linear coverage 70% - 85%
    if linear_coverage < 0.50:
        penalty = (0.50 - linear_coverage) * 90.0
        framing_score -= penalty
        defects.append(f"Product is undersized in frame ({round(linear_coverage * 100, 1)}% span, target > 60%).")
    elif linear_coverage > 0.92:
        penalty = (linear_coverage - 0.92) * 150.0
        framing_score -= penalty
        defects.append(f"Product is oversized / crowded ({round(linear_coverage * 100, 1)}% span).")

    if is_edge_clipped:
        framing_score -= 30.0
        defects.append(f"Product boundary is clipped by image border ({total_edge_touch} edge pixels).")
    elif min_margin < 0.04:
        framing_score -= 15.0
        defects.append(f"Insufficient breathing room near border (margin {round(min_margin * 100, 1)}%).")

    if center_offset > 0.12:
        framing_score -= min(20.0, (center_offset - 0.12) * 80.0)
        defects.append(f"Off-center framing detected (offset {round(center_offset * 100, 1)}%).")

    framing_score = float(np.clip(framing_score, 0.0, 100.0))

    return {
        "has_product": True,
        "bbox": bbox,
        "bbox_occupancy": round(bbox_occupancy, 3),
        "pixel_occupancy": round(pixel_occupancy, 3),
        "linear_coverage": round(linear_coverage, 3),
        "margins": {
            "top": round(margin_top, 3),
            "bottom": round(margin_bottom, 3),
            "left": round(margin_left, 3),
            "right": round(margin_right, 3),
            "min_margin": round(min_margin, 3)
        },
        "center_offset": round(center_offset, 3),
        "is_edge_clipped": is_edge_clipped,
        "edge_touch_pixels": total_edge_touch,
        "framing_score": round(framing_score, 1),
        "defects": defects,
        "num_isolated_components": len(valid_labels)
    }
