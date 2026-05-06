# tem_analyzer_cnn.py
import cv2
import numpy as np
from scipy import ndimage
from skimage import filters, measure, morphology, feature, segmentation
from typing import List, Dict, Optional
import os

try:
    from tensorflow import keras
    import json
    CNN_AVAILABLE = True
except ImportError:
    CNN_AVAILABLE = False
    print("Warning: TensorFlow not available. CNN classifier will not work.")


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


class CNNEVAnalyzer:
    """
    EV analyzer using trained CNN for viability classification.
    Detects particles using traditional CV, classifies using deep learning.
    """

    def __init__(self, nm_per_pixel=0.5, model_path='ev_viability_model.h5', 
                 metadata_path='model_metadata.json'):
        self.nm_per_pixel = nm_per_pixel
        self.model = None
        self.img_size = 128
        self.class_names = ["non_viable", "viable"]
        
        # Load CNN model if available
        if CNN_AVAILABLE and os.path.exists(model_path):
            self.load_cnn_model(model_path, metadata_path)
        else:
            print(f"CNN model not found at {model_path}. Using fallback classification.")
        
        # Thresholds for particle detection
        self.thresholds = {
            "min_size_pixels": 100,
            "min_solidity": 0.5,
        }

    def load_cnn_model(self, model_path: str, metadata_path: str):
        """Load trained CNN model"""
        try:
            self.model = keras.models.load_model(model_path)
            
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                    self.img_size = metadata.get('img_size', 128)
                    self.class_names = metadata.get('class_names', ["non_viable", "viable"])
            
            print(f"CNN model loaded from {model_path}")
        except Exception as e:
            print(f"Error loading CNN model: {e}")
            self.model = None

    def get_best_channel(self, bgr_img):
        """Select channel with best focus."""
        channels = cv2.split(bgr_img)
        scores = [cv2.Laplacian(c, cv2.CV_64F).var() for c in channels]
        return channels[int(np.argmax(scores))]

    def detect_particles(self, image_path: str):
        """Detect particle regions using traditional CV"""
        bgr = cv2.imread(image_path)
        if bgr is None:
            return [], None

        gray_best = self.get_best_channel(bgr)

        # Enhance contrast
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray_best)

        # Threshold
        thresh = filters.threshold_mean(enhanced)
        binary = enhanced > thresh
        binary = morphology.remove_small_objects(binary, min_size=50)
        binary = morphology.closing(binary, morphology.disk(3))

        # Watershed segmentation
        distance = ndimage.distance_transform_edt(binary)
        local_max = feature.peak_local_max(
            distance, min_distance=15, threshold_abs=2, exclude_border=True
        )

        if len(local_max) == 0:
            labels = measure.label(binary)
        else:
            markers = np.zeros(binary.shape, dtype=np.int32)
            for i, (y, x) in enumerate(local_max):
                markers[y, x] = i + 1
            labels = segmentation.watershed(-distance, markers, mask=binary)

        regions = measure.regionprops(labels, intensity_image=enhanced)

        return regions, gray_best

    def extract_particle_patch(self, gray_img: np.ndarray, region) -> Optional[np.ndarray]:
        """Extract particle patch for CNN classification"""
        # Get bounding box
        minr, minc, maxr, maxc = region.bbox
        
        # Add padding
        h, w = gray_img.shape
        pad = 10
        minr = max(0, minr - pad)
        minc = max(0, minc - pad)
        maxr = min(h, maxr + pad)
        maxc = min(w, maxc + pad)
        
        # Extract patch
        patch = gray_img[minr:maxr, minc:maxc]
        
        if patch.size == 0:
            return None
        
        # Resize to model input size
        patch = cv2.resize(patch, (self.img_size, self.img_size))
        
        # Normalize
        patch = patch.astype('float32') / 255.0
        
        return patch

    def classify_particle_cnn(self, patch: np.ndarray) -> Dict:
        """Classify particle using CNN"""
        if self.model is None or patch is None:
            return {'viability': 'needs_review', 'confidence': 0.0}
        
        # Add dimensions
        patch = np.expand_dims(patch, axis=-1)
        patch = np.expand_dims(patch, axis=0)
        
        # Predict
        try:
            prob = self.model.predict(patch, verbose=0)[0][0]
            
            # Classify
            if prob > 0.7:
                viability = "intact"
                confidence = prob
            elif prob < 0.3:
                viability = "not_intact"
                confidence = 1 - prob
            else:
                viability = "needs_review"
                confidence = 0.5
            
            return {
                'viability': viability,
                'confidence': float(confidence),
                'viable_prob': float(prob)
            }
        except Exception as e:
            print(f"CNN classification error: {e}")
            return {'viability': 'needs_review', 'confidence': 0.0}

    def classify_fallback(self, region, enhanced_img):
        """Fallback rule-based classification if CNN not available"""
        if region.area < self.thresholds["min_size_pixels"] or region.solidity < self.thresholds["min_solidity"]:
            return "needs_review"
        
        # Simple heuristic based on solidity
        if region.solidity > 0.8:
            return "intact"
        elif region.solidity > 0.6:
            return "needs_review"
        else:
            return "not_intact"

    def analyze_image(self, image_path: str) -> List[Dict]:
        """
        Main analysis pipeline:
        1. Detect particles using CV
        2. Classify using CNN
        3. Return results
        """
        # Detect particles
        regions, gray_img = self.detect_particles(image_path)
        
        if not regions or gray_img is None:
            return []

        circles = []
        
        for reg in regions:
            # Filter small regions
            if reg.area < self.thresholds["min_size_pixels"]:
                continue
            
            # Extract patch and classify
            if self.model is not None:
                patch = self.extract_particle_patch(gray_img, reg)
                classification = self.classify_particle_cnn(patch)
                viability = classification['viability']
                confidence = classification.get('confidence', 0.0)
            else:
                # Use fallback
                enhanced = gray_img  # Already enhanced in detect_particles
                viability = self.classify_fallback(reg, enhanced)
                confidence = 0.5
            
            # Get centroid and radius
            cy, cx = reg.centroid
            r_px = max(3.0, float(reg.equivalent_diameter) / 2.0)

            diameter_nm = (
                round((r_px * 2.0) * self.nm_per_pixel, 2)
                if self.nm_per_pixel
                else None
            )

            circles.append({
                "number": None,
                "x": round(float(cx), 2),
                "y": round(float(cy), 2),
                "r": round(float(r_px), 2),
                "diameter_nm": diameter_nm,
                "viability": viability,
                "confidence": round(float(confidence), 3),
                "intensity": compute_radial_intensity(gray_img, cx, cy, r_px),
            })

        # Sort and number
        circles.sort(key=lambda c: c["r"], reverse=True)
        for idx, c in enumerate(circles, start=1):
            c["number"] = idx

        return circles


def analyze_image_cnn(image_path: str, nm_per_pixel: float = 0.5, 
                      model_path: str = 'ev_viability_model.h5') -> List[Dict]:
    """
    CNN-based analysis entry point.
    """
    analyzer = CNNEVAnalyzer(
        nm_per_pixel=nm_per_pixel,
        model_path=model_path
    )
    return analyzer.analyze_image(image_path)
