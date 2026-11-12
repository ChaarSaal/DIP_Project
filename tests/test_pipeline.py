"""
PixelSpec Pipeline Integration Tests
"""

import unittest
import numpy as np
import cv2

from pixelspec.pipeline.baseline import run_baseline_pipeline
from pixelspec.pipeline.advanced import run_advanced_pipeline
from pixelspec.pipeline.comparison import compare_pipelines


class TestPipelines(unittest.TestCase):

    def setUp(self):
        # Create a synthetic product on white canvas
        self.img = np.full((300, 300, 3), 255, dtype=np.uint8)
        # Draw product centered
        cv2.rectangle(self.img, (75, 75), (225, 225), (40, 60, 80), -1)
        # Inner detail
        cv2.putText(self.img, "DEMO", (95, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)

    def test_baseline_pipeline(self):
        res = run_baseline_pipeline(self.img)
        self.assertIn("overall_score", res)
        self.assertIn("verdict", res)
        self.assertIn("metrics", res)
        self.assertIn("stage_images", res)
        self.assertIn("annotated", res["stage_images"])

    def test_advanced_pipeline(self):
        res = run_advanced_pipeline(self.img)
        self.assertIn("overall_score", res)
        self.assertIn("verdict", res)
        self.assertIn("recommendations", res)
        self.assertIn("stage_images", res)
        self.assertIn("refined_mask", res["stage_images"])
        self.assertIn("edge_heatmap", res["stage_images"])

    def test_comparison_pipeline(self):
        res = compare_pipelines(self.img)
        self.assertIn("summary", res)
        self.assertIn("baseline", res["summary"])
        self.assertIn("advanced", res["summary"])
        self.assertIn("differences", res["summary"])


if __name__ == "__main__":
    unittest.main()
