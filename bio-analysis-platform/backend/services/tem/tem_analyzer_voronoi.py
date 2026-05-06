# tem_analyzer_voronoi.py
import cv2
import numpy as np
from scipy import ndimage
from scipy.spatial import Voronoi
from skimage import filters, measure, morphology, feature, segmentation
from typing import List, Dict, Tuple


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


def polygon_area(corners):
    """Calculate area of polygon using Shoelace formula."""
    if len(corners) < 3:
        return 0.0
    n = len(corners)
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += corners[i][0] * corners[j][1]
        area -= corners[j][0] * corners[i][1]
    return abs(area) / 2.0


class VoronoiEVAnalyzer:
    """
    Voronoi tessellation-based EV analyzer.
    Uses spatial density instead of individual particle features.
    """

    def __init__(self, nm_per_pixel=0.5):
        self.nm_per_pixel = nm_per_pixel
        self.n_monte_carlo_simulations = 50
        
        # Basic thresholds for initial particle detection
        self.thresholds = {
            "min_size_pixels": 100,  # Smaller than rule-based (we filter by density)
            "min_solidity": 0.4,     # More permissive
        }

    def get_best_channel(self, bgr_img):
        """Select channel with best focus."""
        channels = cv2.split(bgr_img)
        scores = [cv2.Laplacian(c, cv2.CV_64F).var() for c in channels]
        return channels[int(np.argmax(scores))]

    def detect_initial_particles(self, image_path: str) -> Tuple[np.ndarray, np.ndarray]:
        """
        Detect particle centroids for Voronoi analysis.
        Returns: (points array, grayscale image)
        """
        bgr = cv2.imread(image_path)
        if bgr is None:
            return np.array([]), None

        gray_best = self.get_best_channel(bgr)

        # Enhance contrast
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray_best)

        # Threshold
        thresh = filters.threshold_mean(enhanced)
        binary = enhanced > thresh
        binary = morphology.remove_small_objects(binary, min_size=50)
        binary = morphology.closing(binary, morphology.disk(2))

        # Extract centroids
        labels = measure.label(binary)
        regions = measure.regionprops(labels)

        points = []
        for reg in regions:
            if reg.area >= self.thresholds["min_size_pixels"] and reg.solidity >= self.thresholds["min_solidity"]:
                cy, cx = reg.centroid
                points.append([cx, cy])

        return np.array(points), gray_best

    def calculate_voronoi_areas(self, points: np.ndarray, image_shape: Tuple) -> List[float]:
        """
        Calculate Voronoi polygon areas, filtering out edge regions.
        """
        if len(points) < 4:  # Need at least 4 points for meaningful Voronoi
            return []

        # Add boundary points to close outer polygons
        h, w = image_shape
        margin = 100
        boundary_points = np.array([
            [-margin, -margin],
            [w + margin, -margin],
            [w + margin, h + margin],
            [-margin, h + margin],
        ])
        extended_points = np.vstack([points, boundary_points])

        # Compute Voronoi
        vor = Voronoi(extended_points)

        areas = []
        n_original_points = len(points)

        # Calculate areas for original points only (not boundary points)
        for i in range(n_original_points):
            region_index = vor.point_region[i]
            region = vor.regions[region_index]

            # Skip infinite regions or regions touching boundaries
            if -1 in region or len(region) < 3:
                continue

            # Get vertices
            vertices = [vor.vertices[j] for j in region]

            # Check if polygon is inside image bounds
            valid = True
            for v in vertices:
                if v[0] < 0 or v[0] > w or v[1] < 0 or v[1] > h:
                    valid = False
                    break

            if valid:
                area = polygon_area(vertices)
                if area > 0:
                    areas.append(area)

        return areas

    def monte_carlo_baseline(self, n_points: int, image_shape: Tuple) -> List[float]:
        """
        Generate random point distributions and calculate their Voronoi areas.
        This establishes the "null hypothesis" baseline.
        """
        h, w = image_shape
        all_random_areas = []

        for _ in range(self.n_monte_carlo_simulations):
            # Generate random points uniformly
            rand_points = np.random.uniform(0, [w, h], (n_points, 2))

            # Calculate Voronoi areas
            areas = self.calculate_voronoi_areas(rand_points, image_shape)
            all_random_areas.extend(areas)

        return all_random_areas

    def find_density_threshold(self, exp_areas: List[float], rand_areas: List[float]) -> float:
        """
        Find the intersection point A* where experimental PDF crosses random PDF.
        Polygons smaller than A* are considered clusters (EVs).
        """
        if not exp_areas or not rand_areas:
            return 0.0

        # Create histograms
        max_area = max(max(exp_areas), max(rand_areas))
        bins = np.linspace(0, max_area, 100)

        hist_exp, bin_edges = np.histogram(exp_areas, bins=bins, density=True)
        hist_rand, _ = np.histogram(rand_areas, bins=bins, density=True)

        # Find first intersection where exp > rand (cluster zone)
        for i in range(len(hist_exp) - 1):
            if hist_exp[i] > hist_rand[i] and hist_exp[i + 1] <= hist_rand[i + 1]:
                return bin_edges[i + 1]

        # Fallback: use 25th percentile of experimental areas
        return np.percentile(exp_areas, 25)

    def classify_by_density(self, points: np.ndarray, areas: List[float], threshold: float) -> List[str]:
        """
        Classify particles based on their Voronoi polygon area.
        Small area = high density = intact EV cluster
        """
        classifications = []

        for area in areas:
            if area < threshold * 0.5:
                classifications.append("intact")
            elif area < threshold:
                classifications.append("not_intact")
            else:
                classifications.append("needs_review")

        return classifications

    def analyze_image(self, image_path: str) -> List[Dict]:
        """
        Main analysis pipeline using Voronoi tessellation.
        """
        # Step 1: Detect particles
        points, gray_img = self.detect_initial_particles(image_path)

        if len(points) < 4 or gray_img is None:
            return []

        h, w = gray_img.shape

        # Step 2: Calculate Voronoi areas for experimental data
        exp_areas = self.calculate_voronoi_areas(points, (h, w))

        if not exp_areas:
            return []

        # Step 3: Monte Carlo simulation for baseline
        rand_areas = self.monte_carlo_baseline(len(points), (h, w))

        # Step 4: Find density threshold
        threshold_area = self.find_density_threshold(exp_areas, rand_areas)

        # Step 5: Classify particles
        # Match areas back to points (some points may be filtered out at edges)
        circles = []
        
        # Re-compute Voronoi to get point-area mapping
        if len(points) < 4:
            return []
            
        boundary_points = np.array([
            [-100, -100],
            [w + 100, -100],
            [w + 100, h + 100],
            [-100, h + 100],
        ])
        extended_points = np.vstack([points, boundary_points])
        vor = Voronoi(extended_points)

        for i, point in enumerate(points):
            region_index = vor.point_region[i]
            region = vor.regions[region_index]

            if -1 in region or len(region) < 3:
                continue

            vertices = [vor.vertices[j] for j in region]
            
            # Check bounds
            valid = True
            for v in vertices:
                if v[0] < 0 or v[0] > w or v[1] < 0 or v[1] > h:
                    valid = False
                    break

            if not valid:
                continue

            area = polygon_area(vertices)
            if area <= 0:
                continue

            # Classify based on density
            if area < threshold_area * 0.5:
                status = "intact"
            elif area < threshold_area:
                status = "not_intact"
            else:
                status = "needs_review"

            # Estimate radius from area (assuming circular approximation)
            r_px = max(3.0, np.sqrt(area / np.pi))

            diameter_nm = (
                round((r_px * 2.0) * self.nm_per_pixel, 2)
                if self.nm_per_pixel
                else None
            )

            circles.append(
                {
                    "number": None,
                    "x": round(float(point[0]), 2),
                    "y": round(float(point[1]), 2),
                    "r": round(float(r_px), 2),
                    "diameter_nm": diameter_nm,
                    "viability": status,
                    "intensity": compute_radial_intensity(gray_img, point[0], point[1], r_px),
                    "voronoi_area": round(float(area), 2),  # Additional metadata
                    "density_threshold": round(float(threshold_area), 2),
                }
            )

        # Sort and number
        circles.sort(key=lambda c: c["r"], reverse=True)
        for idx, c in enumerate(circles, start=1):
            c["number"] = idx

        return circles


def analyze_image_voronoi(image_path: str, nm_per_pixel: float = 0.5) -> List[Dict]:
    """
    Voronoi-based analysis entry point.
    """
    analyzer = VoronoiEVAnalyzer(nm_per_pixel=nm_per_pixel)
    return analyzer.analyze_image(image_path)
