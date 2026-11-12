"""
PixelSpec Metric Verification Tests
"""

import unittest
import numpy as np
import cv2

from pixelspec.core.color import analyze_background_color, rgb_to_cielab
from pixelspec.core.sharpness import evaluate_sharpness, compute_spatial_sharpness, compute_fft_spectral_ratio
from pixelspec.core.exposure import evaluate_exposure, compute_shannon_entropy
from pixelspec.core.noise import evaluate_noise, estimate_mad_noise
from pixelspec.core.geometry import analyze_product_framing


class TestDIPMetrics(unittest.TestCase):

    def test_sharpness_detection(self):
        # Create sharp checkerboard vs blurred version
        sharp = np.zeros((200, 200, 3), dtype=np.uint8)
        sharp[::20, :] = 255
        sharp[:, ::20] = 255

        blurry = cv2.GaussianBlur(sharp, (15, 15), 5.0)

        res_sharp = evaluate_sharpness(sharp)
        res_blurry = evaluate_sharpness(blurry)

        self.assertGreater(res_sharp["sharpness_score"], res_blurry["sharpness_score"])
        self.assertGreater(res_sharp["tenengrad_gradient"], res_blurry["tenengrad_gradient"])
        self.assertGreater(res_sharp["fft_high_freq_ratio"], res_blurry["fft_high_freq_ratio"])

    def test_noise_estimation(self):
        clean = np.full((200, 200, 3), 128, dtype=np.uint8)
        noisy = np.clip(clean.astype(np.float32) + np.random.normal(0, 15, clean.shape), 0, 255).astype(np.uint8)

        res_clean = evaluate_noise(clean)
        res_noisy = evaluate_noise(noisy)

        self.assertLess(res_clean["estimated_noise_sigma"], 2.0)
        self.assertGreater(res_noisy["estimated_noise_sigma"], 10.0)
        self.assertTrue(res_clean["is_clean"])
        self.assertFalse(res_noisy["is_clean"])

    def test_background_purity(self):
        pure_white = np.full((100, 100, 3), 255, dtype=np.uint8)
        bg_mask = np.ones((100, 100), dtype=bool)

        res = analyze_background_color(pure_white, bg_mask)
        self.assertTrue(res["is_pure_white"])
        self.assertGreaterEqual(res["purity_score"], 95.0)
        self.assertLess(res["median_delta_e"], 2.0)

    def test_framing_clipping(self):
        # Product touching image border
        mask_clipped = np.zeros((100, 100), dtype=bool)
        mask_clipped[0:50, 0:50] = True # touches top and left border

        res = analyze_product_framing(mask_clipped, (100, 100))
        self.assertTrue(res["is_edge_clipped"])
        self.assertGreater(res["edge_touch_pixels"], 0)


if __name__ == "__main__":
    unittest.main()
