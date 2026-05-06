# tem_analyzer.py
import cv2
import numpy as np
from scipy import ndimage
from skimage import filters, measure, morphology, feature, segmentation


def compute_radial_intensity(img_gray, x, y, r, samples=10):
    """Intensity profile (center -> edge)."""
    h, w = img_gray.shape
    cx, cy, r = int(x), int(y), int(r)

    values = []
    for i in range(samples + 1):
        rr = int((i / samples) * r)
        px = min(max(cx + rr, 0), w - 1)
        py = min(max(cy, 0), h - 1)
        values.append(int(img_gray[py, px]))

    return {
        "center_intensity": values[0] if values else None,
        "edge_intensity": values[-1] if values else None,
        "mean_intensity": round(float(np.mean(values)), 2) if values else None,
        "radial_intensity": values,
    }


class TEMExosomeAnalyzer:
    """
    Analyze ONE image and return circles list.
    """

    def __init__(self, nm_per_pixel=0.5):
        self.nm_per_pixel = nm_per_pixel

        self.thresholds = {
            "focus_limit": 15,
            "mem_min_nm": 2.0,
            "mem_max_nm": 6.5,
            "contrast_min": 45,
            "min_size_pixels": 200,
            "min_solidity": 0.65,
        }

    def get_best_channel(self, bgr_img):
        channels = cv2.split(bgr_img)
        scores = [cv2.Laplacian(c, cv2.CV_64F).var() for c in channels]
        return channels[int(np.argmax(scores))]

    def classify_region(self, region, enhanced_img):
        """
        Returns: intact / not_intact / needs_review / background_noise
        """

        if region.area < self.thresholds["min_size_pixels"] or region.solidity < 0.5:
            return "background_noise"

        roi = enhanced_img[region.slice]
        lap_var = cv2.Laplacian(roi, cv2.CV_64F).var()
        is_focused = lap_var > self.thresholds["focus_limit"]

        has_contrast = float(region.mean_intensity) > self.thresholds["contrast_min"]

        if has_contrast and is_focused and region.solidity > self.thresholds["min_solidity"]:
            return "intact"
        if is_focused and region.solidity > self.thresholds["min_solidity"]:
            return "not_intact"
        return "needs_review"

    def detect_particles_voronoi(self, binary):
        distance = ndimage.distance_transform_edt(binary)

        local_max = feature.peak_local_max(
            distance,
            min_distance=15,
            threshold_abs=2,
            exclude_border=True,
        )

        if len(local_max) == 0:
            return measure.label(binary)

        markers = np.zeros(binary.shape, dtype=np.int32)
        for i, (y, x) in enumerate(local_max):
            markers[y, x] = i + 1

        labels = segmentation.watershed(-distance, markers, mask=binary)
        return labels

    def analyze_image(self, image_path: str):
        bgr = cv2.imread(image_path)
        if bgr is None:
            return []

        gray_best = self.get_best_channel(bgr)

        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray_best)

        thresh = filters.threshold_mean(enhanced)
        binary = enhanced > thresh
        binary = morphology.remove_small_objects(binary, min_size=100)
        binary = morphology.closing(binary, morphology.disk(3))

        labels = self.detect_particles_voronoi(binary)
        regions = measure.regionprops(labels, intensity_image=enhanced)

        circles = []
        for reg in regions:
            status = self.classify_region(reg, enhanced)
            if status == "background_noise":
                continue

            cy, cx = reg.centroid  # row,col
            r_px = max(3.0, float(reg.equivalent_diameter) / 2.0)

            diameter_nm = (
                round((r_px * 2.0) * self.nm_per_pixel, 2)
                if self.nm_per_pixel
                else None
            )

            circles.append(
                {
                    "number": None,
                    "x": round(float(cx), 2),
                    "y": round(float(cy), 2),
                    "r": round(float(r_px), 2),
                    "diameter_nm": diameter_nm,
                    "viability": status,
                    "intensity": compute_radial_intensity(gray_best, cx, cy, r_px),
                }
            )

        circles.sort(key=lambda c: c["r"], reverse=True)
        for idx, c in enumerate(circles, start=1):
            c["number"] = idx

        return circles


#def analyze_image_voronoi(image_path: str, nm_per_pixel: float = 0.5):
def analyze_image_rulebased(image_path: str, nm_per_pixel: float = 0.5):
    analyzer = TEMExosomeAnalyzer(nm_per_pixel=nm_per_pixel)
    return analyzer.analyze_image(image_path)
