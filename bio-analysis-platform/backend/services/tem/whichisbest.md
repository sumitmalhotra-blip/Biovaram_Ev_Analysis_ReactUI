# trainning data: 
'/Users/abcd/Downloads/tem-tool-main/backend/filescrmit_3methods/Training Data'


# original images with multiple particles:
/Users/abcd/Downloads/tem-tool-main/backend/filescrmit_3methods/tem_images


# the file which classifies each image intact and non intact images nicely and does  excellent work on outside 7 test image:
/Users/abcd/Downloads/tem-tool-main/backend/filescrmit_3methods/tem_analyzer.py

# the file which gave good detection and prediction on outside trainning data 7 images:
'/Users/abcd/Downloads/tem-tool-main/backend/filescrmit_3methods/tem_analyzer_colourcode_predictions.py'










final one


#!/usr/bin/env python3
"""
TEM EV Analyzer — Majority Vote Classifier
============================================
Three classifiers run independently on every particle:
  1. Rule-based   (OpenCV morphology — membrane integrity)
  2. CNN          (ev_viability_model.h5 — trained MobileNetV2)
  3. Claude Vision (AWS Bedrock — claude-3-5-sonnet)

Final classification = majority vote (2 out of 3).

Scientific ground truth
-----------------------
  VIABLE        membrane forms a complete, continuous closed boundary
                shape is IRRELEVANT (oval, elongated, cup, crown = fine)
  NON-VIABLE    membrane is broken, ruptured, leaking or has huge gaps
  NEEDS_REVIEW  very elongated (eccentricity > 0.88) or overlapping

AWS credentials
---------------
Set these in your .env file or export as environment variables:
  AWS_ACCESS_KEY_ID
  AWS_SECRET_ACCESS_KEY
  AWS_REGION          (default: us-east-1)
  CNN_MODEL_PATH      (default: ev_viability_model.h5)
"""

import os
import cv2
import json
import base64
import logging
import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

# Scientific image processing
from scipy import ndimage as ndi
from skimage.feature import blob_log
from skimage.segmentation import watershed
from skimage.measure import regionprops, label as sk_label

# AWS Bedrock
import boto3
from botocore.exceptions import ClientError

# TensorFlow / Keras CNN
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"   # suppress TF info messages
try:
    import tensorflow as tf
    from tensorflow import keras
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False
    logging.warning("TensorFlow not installed — CNN classifier disabled.")

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# ===========================================================================
# Configuration
# ===========================================================================

class TEMConfig:
    # --- preprocessing ---
    GAUSSIAN_SIGMA        = 1.5
    CLAHE_CLIP            = 2.0
    CLAHE_TILE            = 8

    # --- blob detection ---
    BLOB_MIN_SIGMA        = 3
    BLOB_MAX_SIGMA        = 40
    BLOB_NUM_SIGMA        = 12
    BLOB_THRESHOLD        = 0.08

    # --- size filter ---
    MIN_DIAMETER_PX       = 30
    MAX_DIAMETER_PX       = 300

    # --- rule-based membrane thresholds ---
    SOLIDITY_VIABLE       = 0.55
    EDGE_COVERAGE_VIABLE  = 0.35
    GRADIENT_CONTRAST_MIN = 12
    ECCENTRICITY_REVIEW   = 0.88

    # --- CNN ---
    CNN_MODEL_PATH        = os.getenv("CNN_MODEL_PATH", "ev_viability_best_model.h5")
    CNN_IMG_SIZE          = 128
    CNN_CONFIDENCE_MIN    = 0.55
    CNN_VOTE_WEIGHT       = 1         # CNN counts as 2 votes

    # --- AWS Bedrock ---
    AWS_REGION            = os.getenv("AWS_REGION", "us-east-1")
    AWS_ACCESS_KEY_ID     = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    BEDROCK_MODEL_ID      = "amazon.nova-lite-v1:0"
    BEDROCK_MAX_TOKENS    = 300


# ===========================================================================
# Data classes
# ===========================================================================

@dataclass
class VoteResult:
    classification: str        # viable | non_viable | needs_review
    confidence:     float
    source:         str        # rule_based | cnn | claude_vision


@dataclass
class EVParticle:
    particle_id:          int
    classification:       str        # final majority vote result
    confidence:           float
    votes:                List[VoteResult]
    vote_summary:         str

    center_x:             float
    center_y:             float
    area_px:              float
    diameter_px:          float
    aspect_ratio:         float
    eccentricity:         float
    solidity:             float
    edge_coverage:        float
    gradient_contrast:    float
    membrane_continuous:  bool

    contour:              Optional[np.ndarray] = field(default=None, repr=False)
    cropped_image:        Optional[np.ndarray] = field(default=None, repr=False)
    reason:               str = ""


@dataclass
class AnalysisResult:
    total_detected:   int
    viable_count:     int
    non_viable_count: int
    review_count:     int
    viable_pct:       float
    particles:        List[EVParticle]
    annotated_image:  Optional[np.ndarray] = field(default=None, repr=False)
    detection_image:  Optional[np.ndarray] = field(default=None, repr=False)


# ===========================================================================
# Classifier 1 — Rule-based (membrane integrity)
# ===========================================================================

class RuleBasedClassifier:
    """
    Checks membrane integrity using morphology metrics.
    ONLY criterion: is the membrane closed and continuous?
    Shape (oval, elongated, cup) does NOT affect the result.
    """

    def __init__(self, cfg: TEMConfig):
        self.cfg = cfg

    def classify(
        self,
        solidity:            float,
        eccentricity:        float,
        edge_coverage:       float,
        gradient_contrast:   float,
        membrane_continuous: bool,
    ) -> VoteResult:

        # needs_review: very elongated
        if eccentricity > self.cfg.ECCENTRICITY_REVIEW:
            return VoteResult("needs_review", 0.5, "rule_based")

        # count broken membrane signals
        broken = 0
        if not membrane_continuous:           broken += 2
        if solidity < self.cfg.SOLIDITY_VIABLE:             broken += 1
        if edge_coverage < self.cfg.EDGE_COVERAGE_VIABLE:   broken += 1
        if gradient_contrast < self.cfg.GRADIENT_CONTRAST_MIN: broken += 1

        if broken >= 2:
            conf = min(0.95, 0.5 + broken * 0.1)
            return VoteResult("non_viable", conf, "rule_based")

        intact = (2 if membrane_continuous else 0) + \
                 (1 if solidity >= self.cfg.SOLIDITY_VIABLE else 0) + \
                 (1 if edge_coverage >= self.cfg.EDGE_COVERAGE_VIABLE else 0) + \
                 (1 if gradient_contrast >= self.cfg.GRADIENT_CONTRAST_MIN else 0)
        conf = min(0.98, 0.5 + intact * 0.1)
        return VoteResult("viable", conf, "rule_based")


# ===========================================================================
# Classifier 2 — CNN (MobileNetV2)
# ===========================================================================

class CNNClassifier:
    """
    Loads ev_viability_model.h5 and classifies cropped particle images.
    """

    def __init__(self, cfg: TEMConfig):
        self.cfg   = cfg
        self.model = None
        self._load_model()

    def _load_model(self):
        if not TF_AVAILABLE:
            logger.warning("CNN: TensorFlow not available.")
            return
        if not os.path.exists(self.cfg.CNN_MODEL_PATH):
            logger.warning(f"CNN: Model not found at {self.cfg.CNN_MODEL_PATH}")
            return
        try:
            self.model = keras.models.load_model(self.cfg.CNN_MODEL_PATH)
            logger.info(f"CNN: Loaded model from {self.cfg.CNN_MODEL_PATH}")
        except Exception as e:
            logger.error(f"CNN: Failed to load model — {e}")

    def classify(self, cropped_bgr: np.ndarray) -> VoteResult:
        if self.model is None:
            return VoteResult("needs_review", 0.5, "cnn")

        try:
            # Preprocess — match training pipeline
            img = cv2.resize(cropped_bgr, (self.cfg.CNN_IMG_SIZE, self.cfg.CNN_IMG_SIZE))
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            img = img.astype("float32") / 255.0
            img = np.expand_dims(img, axis=0)    # (1, 128, 128, 3)

            prob = float(self.model.predict(img, verbose=0)[0][0])

            # prob > 0.5 → viable (label=1), else non_viable (label=0)
            if prob > 0.5:
                conf = prob
                if conf < self.cfg.CNN_CONFIDENCE_MIN:
                    return VoteResult("needs_review", conf, "cnn")
                return VoteResult("viable", conf, "cnn")
            else:
                conf = 1.0 - prob
                if conf < self.cfg.CNN_CONFIDENCE_MIN:
                    return VoteResult("needs_review", conf, "cnn")
                return VoteResult("non_viable", conf, "cnn")

        except Exception as e:
            logger.error(f"CNN inference error: {e}")
            return VoteResult("needs_review", 0.5, "cnn")


# ===========================================================================
# Classifier 3 — Claude Vision via AWS Bedrock
# ===========================================================================

CLAUDE_SYSTEM_PROMPT = """You are an expert in Transmission Electron Microscopy (TEM) 
analysis of Extracellular Vesicles (EVs) and exosomes.

Your ONLY job is to assess membrane integrity. 

RULES (from domain expert):
- VIABLE: membrane forms a complete, continuous closed boundary. 
  Shape does NOT matter — oval, elongated, cup-shaped, crown = all VIABLE 
  if membrane is intact.
- NON_VIABLE: membrane is broken, ruptured, leaking, split, or has huge gaps.
- NEEDS_REVIEW: very elongated particles or overlapping particles where 
  you cannot clearly determine membrane integrity.

Respond ONLY with valid JSON. No explanation outside the JSON.
Format:
{
  "classification": "viable" | "non_viable" | "needs_review",
  "confidence": 0.0-1.0,
  "reason": "one sentence explanation"
}"""

CLAUDE_USER_PROMPT = """Analyze this cropped TEM image of a single EV/exosome particle.
Assess ONLY the membrane integrity.
Is the outer membrane boundary complete and continuous?
Respond with JSON only."""


class ClaudeVisionClassifier:
    """
    Sends cropped particle image to Claude via AWS Bedrock Converse API.
    Uses AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY from environment.
    """

    def __init__(self, cfg: TEMConfig):
        self.cfg    = cfg
        self.client = None
        self._init_client()

    def _init_client(self):
        if not self.cfg.AWS_ACCESS_KEY_ID or not self.cfg.AWS_SECRET_ACCESS_KEY:
            logger.warning("Claude Vision: AWS credentials not set. "
                           "Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY.")
            return
        try:
            self.client = boto3.client(
                service_name          = "bedrock-runtime",
                region_name           = self.cfg.AWS_REGION,
                aws_access_key_id     = self.cfg.AWS_ACCESS_KEY_ID,
                aws_secret_access_key = self.cfg.AWS_SECRET_ACCESS_KEY,
            )
            logger.info("Claude Vision: AWS Bedrock client initialised.")
        except Exception as e:
            logger.error(f"Claude Vision: Failed to init Bedrock client — {e}")

    def classify(self, cropped_bgr: np.ndarray) -> VoteResult:
        if self.client is None:
            return VoteResult("needs_review", 0.5, "claude_vision")

        try:
            # Encode cropped image as base64 PNG
            _, buf     = cv2.imencode(".png", cropped_bgr)
            img_b64    = base64.b64encode(buf.tobytes()).decode("utf-8")

            response = self.client.converse(
                modelId = self.cfg.BEDROCK_MODEL_ID,
                system  = [{"text": CLAUDE_SYSTEM_PROMPT}],
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {
                                "image": {
                                    "format": "png",
                                    "source": {"bytes": buf.tobytes()}
                                }
                            },
                            {"text": CLAUDE_USER_PROMPT}
                        ]
                    }
                ],
                inferenceConfig = {
                    "maxTokens":   self.cfg.BEDROCK_MAX_TOKENS,
                    "temperature": 0.1,    # low temperature = more consistent
                }
            )

            raw_text = response["output"]["message"]["content"][0]["text"]
            parsed   = self._parse_response(raw_text)
            return VoteResult(
                parsed.get("classification", "needs_review"),
                float(parsed.get("confidence", 0.5)),
                "claude_vision"
            )

        except ClientError as e:
            logger.error(f"Claude Vision: Bedrock API error — {e}")
            return VoteResult("needs_review", 0.5, "claude_vision")
        except Exception as e:
            logger.error(f"Claude Vision: Unexpected error — {e}")
            return VoteResult("needs_review", 0.5, "claude_vision")

    @staticmethod
    def _parse_response(text: str) -> dict:
        """Extract JSON from Claude's response robustly."""
        try:
            # Try direct parse
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass
        try:
            # Extract JSON block if wrapped in markdown
            start = text.find("{")
            end   = text.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
        except Exception:
            pass
        return {"classification": "needs_review", "confidence": 0.5,
                "reason": "Could not parse Claude response"}


# ===========================================================================
# Majority Vote
# ===========================================================================

def majority_vote(votes: List[VoteResult], cnn_weight: int = 2) -> Tuple[str, float, str]:
    """
    Weighted majority vote. CNN counts as 2 votes, others as 1.
    Claude Vision votes with confidence=0.50 are treated as abstain (API failed).
    If all active voters disagree → needs_review.
    Returns (classification, avg_confidence, summary).
    """
    # Filter out abstaining votes (Claude failed = confidence exactly 0.5)
    active_votes = [v for v in votes
                    if not (v.source == "claude_vision" and v.confidence == 0.5)]

    vote_pool = active_votes if active_votes else votes

    counts = {"viable": 0, "non_viable": 0, "needs_review": 0}
    for v in vote_pool:
        cls = v.classification if v.classification in counts else "needs_review"
        weight = cnn_weight if v.source == "cnn" else 1
        counts[cls] += weight

    winner    = max(counts, key=counts.get)
    win_count = counts[winner]

    if win_count == 1:
        winner    = "needs_review"
        win_count = 0

    winning_votes = [v for v in vote_pool
                     if v.classification == winner or winner == "needs_review"]
    avg_conf = np.mean([v.confidence for v in winning_votes]) if winning_votes else 0.5

    claude_note = "claude=abstain" if len(active_votes) < len(votes) else \
                  f"claude={votes[2].classification}({votes[2].confidence:.2f})"

    summary = (
        f"rule_based={votes[0].classification}({votes[0].confidence:.2f}) | "
        f"cnn={votes[1].classification}({votes[1].confidence:.2f}) | "
        f"{claude_note} | "
        f"vote={winner}({win_count}/{len(vote_pool)})"
    )
    return winner, float(avg_conf), summary


# ===========================================================================
# Main analyser
# ===========================================================================

class TEMAnalyzer:
    """
    Full pipeline:
      Detection (OpenCV) → Three classifiers → Majority vote → Annotated image
    """

    COLOUR = {
        "viable":       (0,   200,  0),    # green
        "non_viable":   (0,   0,    220),  # red   (BGR)
        "needs_review": (0,   200,  220),  # yellow (BGR)
    }
    OUTLINE_COLOUR = (200, 100, 0)          # blue outline

    def __init__(self, config: TEMConfig = None):
        self.cfg     = config or TEMConfig()
        self.rule    = RuleBasedClassifier(self.cfg)
        self.cnn     = CNNClassifier(self.cfg)
        self.claude  = ClaudeVisionClassifier(self.cfg)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(self, image_bgr: np.ndarray) -> AnalysisResult:
        gray         = self._to_gray(image_bgr)
        preprocessed = self._preprocess(gray)
        centers      = self._detect_blobs(preprocessed)
        label_map    = self._watershed_segment(preprocessed, centers)
        particles    = self._process_particles(image_bgr, gray, preprocessed, label_map)
        annotated    = self._draw_results(image_bgr, particles)
        detection    = self._draw_detection_only(image_bgr, particles)

        viable     = [p for p in particles if p.classification == "viable"]
        non_viable = [p for p in particles if p.classification == "non_viable"]
        review     = [p for p in particles if p.classification == "needs_review"]
        total      = len(particles)

        return AnalysisResult(
            total_detected   = total,
            viable_count     = len(viable),
            non_viable_count = len(non_viable),
            review_count     = len(review),
            viable_pct       = (len(viable) / total * 100) if total else 0.0,
            particles        = particles,
            annotated_image  = annotated,
            detection_image  = detection,
        )

    # ------------------------------------------------------------------
    # Steps 1-2: Preprocessing
    # ------------------------------------------------------------------

    def _to_gray(self, img):
        return img if len(img.shape) == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    def _preprocess(self, gray):
        blurred = cv2.GaussianBlur(gray, (0, 0), self.cfg.GAUSSIAN_SIGMA)
        clahe   = cv2.createCLAHE(
            clipLimit    = self.cfg.CLAHE_CLIP,
            tileGridSize = (self.cfg.CLAHE_TILE, self.cfg.CLAHE_TILE)
        )
        return clahe.apply(blurred)

    # ------------------------------------------------------------------
    # Step 3: Blob detection — one centre per EV
    # ------------------------------------------------------------------

    def _detect_blobs(self, preprocessed):
        img_f  = preprocessed.astype(np.float32) / 255.0
        blobs  = blob_log(img_f,
                          min_sigma=self.cfg.BLOB_MIN_SIGMA,
                          max_sigma=self.cfg.BLOB_MAX_SIGMA,
                          num_sigma=self.cfg.BLOB_NUM_SIGMA,
                          threshold=self.cfg.BLOB_THRESHOLD)
        if blobs is None or len(blobs) == 0:
            blobs = blob_log(1.0 - img_f,
                             min_sigma=self.cfg.BLOB_MIN_SIGMA,
                             max_sigma=self.cfg.BLOB_MAX_SIGMA,
                             num_sigma=self.cfg.BLOB_NUM_SIGMA,
                             threshold=self.cfg.BLOB_THRESHOLD)
        result = []
        for b in (blobs if blobs is not None else []):
            r, c, sigma = b
            radius = sigma * np.sqrt(2)
            diam   = radius * 2
            if self.cfg.MIN_DIAMETER_PX <= diam <= self.cfg.MAX_DIAMETER_PX:
                result.append((int(r), int(c), float(radius)))
        return result

    # ------------------------------------------------------------------
    # Step 4: Watershed segmentation
    # ------------------------------------------------------------------

    def _watershed_segment(self, preprocessed, centers):
        h, w    = preprocessed.shape
        markers = np.zeros((h, w), dtype=np.int32)
        for idx, (r, c, radius) in enumerate(centers, start=1):
            rr = int(np.clip(r, 0, h - 1))
            cc = int(np.clip(c, 0, w - 1))
            cv2.circle(markers, (cc, rr), max(1, int(radius * 0.3)), idx, -1)
        if np.max(markers) == 0:
            return np.zeros((h, w), dtype=np.int32)
        gradient = cv2.morphologyEx(
            preprocessed,
            cv2.MORPH_GRADIENT,
            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        )
        return watershed(gradient, markers, compactness=0.001)

    # ------------------------------------------------------------------
    # Step 5: Feature extraction + three classifiers + majority vote
    # ------------------------------------------------------------------

    def _process_particles(self, image_bgr, gray, preprocessed, label_map):
        particles = []
        edge_map  = cv2.Canny(preprocessed, 30, 80)
        props     = regionprops(label_map, intensity_image=gray)

        for prop in props:
            diam = 2 * np.sqrt(prop.area / np.pi)
            if diam < self.cfg.MIN_DIAMETER_PX or diam > self.cfg.MAX_DIAMETER_PX:
                continue

            mask = (label_map == prop.label).astype(np.uint8) * 255
            contours, _ = cv2.findContours(
                mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            if not contours:
                continue
            contour = max(contours, key=cv2.contourArea)

            # --- geometry ---
            major        = max(prop.major_axis_length, 1)
            minor        = max(prop.minor_axis_length, 1)
            aspect_ratio = major / minor
            eccentricity = prop.eccentricity
            solidity     = prop.solidity

            # --- membrane metrics ---
            edge_cov   = self._edge_coverage(mask, edge_map)
            grad_cont  = self._gradient_contrast(gray, mask)
            mem_cont   = self._membrane_continuous(mask, edge_map, edge_cov)

            # --- crop particle for CNN and Claude ---
            cropped    = self._crop_particle(image_bgr, mask)

            # --- run three classifiers ---
            vote_rule  = self.rule.classify(
                solidity, eccentricity, edge_cov, grad_cont, mem_cont
            )
            vote_cnn   = self.cnn.classify(cropped)
            vote_claude = self.claude.classify(cropped)

            votes      = [vote_rule, vote_cnn, vote_claude]
            final_cls, final_conf, summary = majority_vote(votes)

            cy, cx = prop.centroid
            particles.append(EVParticle(
                particle_id         = prop.label,
                classification      = final_cls,
                confidence          = final_conf,
                votes               = votes,
                vote_summary        = summary,
                center_x            = cx,
                center_y            = cy,
                area_px             = prop.area,
                diameter_px         = diam,
                aspect_ratio        = aspect_ratio,
                eccentricity        = eccentricity,
                solidity            = solidity,
                edge_coverage       = edge_cov,
                gradient_contrast   = grad_cont,
                membrane_continuous = mem_cont,
                contour             = contour,
                cropped_image       = cropped,
            ))

        logger.info(
            f"Processed {len(particles)} particles. "
            f"Viable={sum(1 for p in particles if p.classification=='viable')} "
            f"NonViable={sum(1 for p in particles if p.classification=='non_viable')} "
            f"Review={sum(1 for p in particles if p.classification=='needs_review')}"
        )
        return particles

    # ------------------------------------------------------------------
    # Membrane integrity helpers
    # ------------------------------------------------------------------

    def _edge_coverage(self, mask, edge_map):
        k        = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        boundary = cv2.subtract(cv2.dilate(mask, k), cv2.erode(mask, k))
        bp       = np.count_nonzero(boundary)
        if bp == 0:
            return 0.0
        return np.count_nonzero(cv2.bitwise_and(boundary, edge_map)) / bp

    def _gradient_contrast(self, gray, mask):
        k      = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        outer  = cv2.subtract(cv2.dilate(mask, k, iterations=2), mask)
        inside = gray[mask > 0]
        outside = gray[outer > 0]
        if len(inside) == 0 or len(outside) == 0:
            return 0.0
        return float(abs(np.mean(inside) - np.mean(outside)))

    def _membrane_continuous(self, mask, edge_map, edge_cov):
        n, _ = cv2.connectedComponents(mask)
        if n > 2:
            return False
        if edge_cov < self.cfg.EDGE_COVERAGE_VIABLE:
            return False
        contours, _ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        if not contours:
            return False
        c    = max(contours, key=cv2.contourArea)
        hull = cv2.convexHull(c)
        hm   = np.zeros_like(mask)
        cv2.drawContours(hm, [hull], -1, 255, -1)
        ha   = np.count_nonzero(hm)
        return (np.count_nonzero(mask) / ha >= 0.45) if ha > 0 else False

    def _crop_particle(self, image_bgr, mask, padding=10):
        """Crop bounding box of particle with padding."""
        coords = cv2.findNonZero(mask)
        if coords is None:
            return image_bgr
        x, y, w, h = cv2.boundingRect(coords)
        ih, iw     = image_bgr.shape[:2]
        x1 = max(0, x - padding)
        y1 = max(0, y - padding)
        x2 = min(iw, x + w + padding)
        y2 = min(ih, y + h + padding)
        return image_bgr[y1:y2, x1:x2]

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def _draw_results(self, image_bgr, particles):
        output  = image_bgr.copy()
        overlay = image_bgr.copy()
        for p in particles:
            if p.contour is None:
                continue
            colour = self.COLOUR.get(p.classification, (128, 128, 128))
            cv2.drawContours(overlay, [p.contour], -1, colour, -1)
            cv2.drawContours(output,  [p.contour], -1, self.OUTLINE_COLOUR, 1)
        cv2.addWeighted(overlay, 0.35, output, 0.65, 0, output)
        for p in particles:
            lbl = {"viable": "V", "non_viable": "NV", "needs_review": "R"}.get(
                p.classification, "?"
            )
            cv2.putText(
                output, lbl,
                (int(p.center_x) - 6, int(p.center_y) + 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.35,
                self.COLOUR.get(p.classification, (255, 255, 255)),
                1, cv2.LINE_AA
            )
        return output

    def _draw_detection_only(self, image_bgr, particles):
        output = image_bgr.copy()
        for p in particles:
            if p.contour is None:
                continue
            colour = (0, 0, 220) if p.classification == "non_viable" \
                     else self.OUTLINE_COLOUR
            cv2.drawContours(output, [p.contour], -1, colour, 1)
        return output


# ===========================================================================
# Drop-in API wrapper (compatible with existing main.py / FastAPI routes)
# ===========================================================================

def analyze_image(image_bgr: np.ndarray, config: TEMConfig = None) -> dict:
    """
    Drop-in wrapper for FastAPI routes.

    Returns:
    {
        "total":          int,
        "viable":         int,
        "non_viable":     int,
        "needs_review":   int,
        "viable_pct":     float,
        "particles":      [ {id, classification, confidence, votes, ...} ],
        "annotated_image": np.ndarray (BGR),
        "detection_image": np.ndarray (BGR),
    }
    """
    analyzer = TEMAnalyzer(config)
    result   = analyzer.analyze(image_bgr)

    return {
        "total":          result.total_detected,
        "viable":         result.viable_count,
        "non_viable":     result.non_viable_count,
        "needs_review":   result.review_count,
        "viable_pct":     round(result.viable_pct, 2),
        "particles": [
            {
                "id":                p.particle_id,
                "classification":    p.classification,
                "confidence":        round(p.confidence, 3),
                "votes": {
                    "rule_based":    p.votes[0].classification,
                    "cnn":           p.votes[1].classification,
                    "claude_vision": p.votes[2].classification,
                },
                "vote_summary":      p.vote_summary,
                "center":            (round(p.center_x, 1), round(p.center_y, 1)),
                "diameter_px":       round(p.diameter_px, 1),
                "aspect_ratio":      round(p.aspect_ratio, 3),
                "eccentricity":      round(p.eccentricity, 3),
                "solidity":          round(p.solidity, 3),
                "edge_coverage":     round(p.edge_coverage, 3),
                "gradient_contrast": round(p.gradient_contrast, 1),
                "membrane_intact":   p.membrane_continuous,
            }
            for p in result.particles
        ],
        "annotated_image": result.annotated_image,
        "detection_image": result.detection_image,
    }


# ===========================================================================
# Quick test — python tem_analyzer.py your_image.png
# ===========================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python tem_analyzer.py <image_path>")
        print("       AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY must be set.")
        sys.exit(1)

    path = sys.argv[1]
    if not os.path.exists(path):
        print(f"File not found: {path}")
        sys.exit(1)

    img    = cv2.imread(path)
    result = analyze_image(img)

    print(f"\n{'='*55}")
    print(f"  TEM EV Analysis — {os.path.basename(path)}")
    print(f"{'='*55}")
    print(f"  Total detected : {result['total']}")
    print(f"  Viable         : {result['viable']}  ({result['viable_pct']:.1f}%)")
    print(f"  Non-viable     : {result['non_viable']}")
    print(f"  Needs review   : {result['needs_review']}")
    print(f"{'='*55}")
    print("\nPer-particle votes:")
    for p in result["particles"][:5]:   # show first 5
        print(f"  #{p['id']:3d}  {p['classification']:12s}  {p['vote_summary']}")
    if len(result["particles"]) > 5:
        print(f"  ... and {len(result['particles'])-5} more")

    base = os.path.splitext(path)[0]
    cv2.imwrite(f"{base}_annotated.png", result["annotated_image"])
    cv2.imwrite(f"{base}_detection.png", result["detection_image"])
    print(f"\nSaved: {base}_annotated.png")
    print(f"Saved: {base}_detection.png")







(venv_tf) abcd@abcds-MacBook-Pro filescrmit_3methods % python test_accuracy.py 2>/dev/null
=== VIABLE IMAGES (expected: viable) ===
  A1.png                       viable=1/6  (17%)
  A2.png                       viable=1/1  (100%)
  B10.png                      viable=1/1  (100%)
  B11.png                      viable=2/2  (100%)
  B12.png                      viable=1/1  (100%)
  B13.png                      viable=2/2  (100%)
  B14.png                      viable=1/2  (50%)
  B15.png                      viable=1/1  (100%)
  B16.png                      viable=1/1  (100%)
  B17.png                      viable=1/5  (20%)
  B18.png                      viable=2/3  (67%)
  B19.png                      viable=1/1  (100%)
  B20.png                      viable=1/1  (100%)
  B21.png                      viable=0/1  (0%)
  B22.png                      viable=1/5  (20%)
  B3.png                       viable=1/1  (100%)
  B4.png                       viable=1/1  (100%)
  B5.png                       viable=2/4  (50%)
  B6.png                       viable=0/2  (0%)
  B7.png                       viable=1/1  (100%)
  B8.png                       viable=2/3  (67%)
  B9.png                       viable=2/2  (100%)
  Screenshot 2026-02-24 at     viable=1/1  (100%)
  Screenshot 2026-02-24 at     viable=2/2  (100%)
  Screenshot 2026-02-24 at     viable=2/2  (100%)
  Screenshot 2026-02-24 at     viable=1/1  (100%)
  Screenshot 2026-02-24 at     viable=0/1  (0%)
  Screenshot 2026-02-24 at     viable=1/1  (100%)
  Screenshot 2026-02-24 at     viable=1/1  (100%)
  Screenshot 2026-02-24 at     viable=1/1  (100%)
  Screenshot 2026-02-24 at     viable=1/1  (100%)
  Screenshot 2026-02-24 at     viable=1/1  (100%)

=== NON-VIABLE IMAGES (expected: non_viable) ===
  NiB1.png                     non_viable=1/1  (100%)
  NiB10.png                    non_viable=0/1  (0%)
  NiB11.png                    non_viable=0/2  (0%)
  NiB12.png                    non_viable=1/1  (100%)
  NiB13.png                    non_viable=2/2  (100%)
  NiB14.png                    non_viable=1/1  (100%)
  NiB15.png                    non_viable=1/1  (100%)
  NiB2.png                     non_viable=1/1  (100%)
  NiB3.png                     non_viable=0/1  (0%)
  NiB4.png                     non_viable=0/1  (0%)
  NiB5.png                     non_viable=1/2  (50%)
  NiB6.png                     non_viable=1/1  (100%)
  NiB7.png                     non_viable=3/3  (100%)
  NiB8.png                     non_viable=1/1  (100%)
  NiB9.png                     non_viable=0/1  (0%)
  nv1.png                      non_viable=10/10  (100%)
  nv10.png                     non_viable=5/5  (100%)
  nv11.png                     non_viable=5/5  (100%)
  nv12.png                     non_viable=28/45  (62%)
  nv13.png                     non_viable=78/123  (63%)
  nv14.png                     non_viable=20/27  (74%)
  nv2.png                      non_viable=8/8  (100%)
  nv3.png                      non_viable=7/7  (100%)
  nv4.png                      non_viable=6/6  (100%)
  nv5.png                      non_viable=5/5  (100%)
  nv6.png                      non_viable=9/9  (100%)
  nv7.png                      non_viable=5/6  (83%)
  nv8.png                      non_viable=3/3  (100%)
  nv9.png                      non_viable=5/5  (100%)

==================================================
Viable accuracy:     37/59 (62.7%)
Non-viable accuracy: 207/284 (72.9%)
Overall accuracy:    244/343 (71.1%)
==================================================
(venv_tf) abcd@abcds-MacBook-Pro filescrmit_3methods % >....                                      
    img = cv2.imread(f)
    if img is None:
        print(f'{os.path.basename(f):12s}  Could not read')
        continue
    r = tem_analyzer.analyze_image(img)
    for p in r['particles']:
        rb_cls   = p['votes']['rule_based']
        cnn_cls  = p['votes']['cnn']
        nova_cls = p['votes']['claude_vision']

        # get confidence per classifier from votes list
        rb_conf   = p['votes']['rule_based']
        votes_raw = r['particles']

        summary = p['vote_summary']
        # parse confidences from summary string
        import re
        confs = re.findall(r'(\w+)=(\w+)\(([\d.]+)\)', summary)
        conf_map = {c[0]: (c[1], float(c[2])) for c in confs}

        rb   = conf_map.get('rule_based', (rb_cls, 0))
        cnn  = conf_map.get('cnn', (cnn_cls, 0))
        nova = conf_map.get('claude', (nova_cls, 0))

        print(f'{os.path.basename(f):12s}  rule={rb[0]:12s}({rb[1]:.0%})  cnn={cnn[0]:12s}({cnn[1]:.0%})  nova={nova[0]:12s}({nova[1]:.0%})  FINAL={p[\"classification\"]:12s}({p[\"confidence\"]:.0%})')
" 2>/dev/null











Great question! Here's exactly how the final decision was made for test1:

Votes:

Rule-based → non_viable (90%)
CNN → needs_review (51%)
Nova → viable (95%)
Majority vote logic (each = 1 vote):

non_viable: 1 vote
needs_review: 1 vote
viable: 1 vote
It's a 3-way tie — no majority winner. When there's a tie, the system falls back to needs_review because it can't confidently pick a winner.

Compare test3 where it worked:

Rule-based → non_viable
CNN → viable
Nova → viable
viable gets 2 votes → clear majority → FINAL = viable ✅

So the voting logic is:

2 out of 3 agree → that class wins
All 3 disagree → needs_review








Image	Final Prediction	Confidence (approx)	Interpretation
test1	needs_review	79%	borderline vesicle
test2	non_viable	84%	debris / artifact
test3	viable	93%	intact vesicle
test4	non_viable	94%	cluster / damaged
test5	non_viable	99–100%	debris region
test6	non_viable	~90%	collapsed / artifact
test7	needs_review	~75%	mixed morphology






— ## Detection and colour coding in test images###




#!/usr/bin/env python3
"""
TEM EV Analyzer — Majority Vote Classifier
============================================
Three classifiers run independently on every particle:
  1. Rule-based   (OpenCV morphology — membrane integrity)
  2. CNN          (ev_viability_model.h5 — trained MobileNetV2)
  3. Claude Vision (AWS Bedrock — claude-3-5-sonnet)

Final classification = majority vote (2 out of 3).

Scientific ground truth
-----------------------
  VIABLE        membrane forms a complete, continuous closed boundary
                shape is IRRELEVANT (oval, elongated, cup, crown = fine)
  NON-VIABLE    membrane is broken, ruptured, leaking or has huge gaps
  NEEDS_REVIEW  very elongated (eccentricity > 0.88) or overlapping

AWS credentials
---------------
Set these in your .env file or export as environment variables:
  AWS_ACCESS_KEY_ID
  AWS_SECRET_ACCESS_KEY
  AWS_REGION          (default: us-east-1)
  CNN_MODEL_PATH      (default: ev_viability_model.h5)
"""

import os
import cv2
import json
import base64
import logging
import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

# Scientific image processing
from scipy import ndimage as ndi
from skimage.feature import blob_log
from skimage.segmentation import watershed
from skimage.measure import regionprops, label as sk_label

# AWS Bedrock
import boto3
from botocore.exceptions import ClientError

# TensorFlow / Keras CNN
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"   # suppress TF info messages
try:
    import tensorflow as tf
    from tensorflow import keras
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False
    logging.warning("TensorFlow not installed — CNN classifier disabled.")

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# ===========================================================================
# Configuration
# ===========================================================================

class TEMConfig:
    # --- preprocessing ---
    GAUSSIAN_SIGMA        = 1.5
    CLAHE_CLIP            = 2.0
    CLAHE_TILE            = 8

    # --- blob detection ---
    BLOB_MIN_SIGMA        = 3
    BLOB_MAX_SIGMA        = 60
    BLOB_NUM_SIGMA        = 12
    BLOB_THRESHOLD        = 0.35

    # --- size filter ---
    MIN_DIAMETER_PX       = 50
    MAX_DIAMETER_PX       = 300

    # --- rule-based membrane thresholds ---
    SOLIDITY_VIABLE       = 0.55
    EDGE_COVERAGE_VIABLE  = 0.35
    GRADIENT_CONTRAST_MIN = 12
    ECCENTRICITY_REVIEW   = 0.88

    # --- CNN ---
    CNN_MODEL_PATH        = os.getenv("CNN_MODEL_PATH", "ev_viability_best_model.h5")
    CNN_IMG_SIZE          = 128
    CNN_CONFIDENCE_MIN    = 0.55
    CNN_VOTE_WEIGHT       = 1         # CNN counts as 2 votes

    # --- AWS Bedrock ---
    AWS_REGION            = os.getenv("AWS_REGION", "us-east-1")
    AWS_ACCESS_KEY_ID     = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    BEDROCK_MODEL_ID      = "amazon.nova-lite-v1:0"
    BEDROCK_MAX_TOKENS    = 300


# ===========================================================================
# Data classes
# ===========================================================================

@dataclass
class VoteResult:
    classification: str        # viable | non_viable | needs_review
    confidence:     float
    source:         str        # rule_based | cnn | claude_vision


@dataclass
class EVParticle:
    particle_id:          int
    classification:       str        # final majority vote result
    confidence:           float
    votes:                List[VoteResult]
    vote_summary:         str

    center_x:             float
    center_y:             float
    area_px:              float
    diameter_px:          float
    aspect_ratio:         float
    eccentricity:         float
    solidity:             float
    edge_coverage:        float
    gradient_contrast:    float
    membrane_continuous:  bool

    contour:              Optional[np.ndarray] = field(default=None, repr=False)
    cropped_image:        Optional[np.ndarray] = field(default=None, repr=False)
    reason:               str = ""


@dataclass
class AnalysisResult:
    total_detected:   int
    viable_count:     int
    non_viable_count: int
    review_count:     int
    viable_pct:       float
    particles:        List[EVParticle]
    annotated_image:  Optional[np.ndarray] = field(default=None, repr=False)
    detection_image:  Optional[np.ndarray] = field(default=None, repr=False)


# ===========================================================================
# Classifier 1 — Rule-based (membrane integrity)
# ===========================================================================

class RuleBasedClassifier:
    """
    Checks membrane integrity using morphology metrics.
    ONLY criterion: is the membrane closed and continuous?
    Shape (oval, elongated, cup) does NOT affect the result.
    """

    def __init__(self, cfg: TEMConfig):
        self.cfg = cfg

    def classify(
        self,
        solidity:            float,
        eccentricity:        float,
        edge_coverage:       float,
        gradient_contrast:   float,
        membrane_continuous: bool,
    ) -> VoteResult:

        # needs_review: very elongated
        if eccentricity > self.cfg.ECCENTRICITY_REVIEW:
            return VoteResult("needs_review", 0.5, "rule_based")

        # count broken membrane signals
        broken = 0
        if not membrane_continuous:           broken += 2
        if solidity < self.cfg.SOLIDITY_VIABLE:             broken += 1
        if edge_coverage < self.cfg.EDGE_COVERAGE_VIABLE:   broken += 1
        if gradient_contrast < self.cfg.GRADIENT_CONTRAST_MIN: broken += 1

        if broken >= 2:
            conf = min(0.95, 0.5 + broken * 0.1)
            return VoteResult("non_viable", conf, "rule_based")

        intact = (2 if membrane_continuous else 0) + \
                 (1 if solidity >= self.cfg.SOLIDITY_VIABLE else 0) + \
                 (1 if edge_coverage >= self.cfg.EDGE_COVERAGE_VIABLE else 0) + \
                 (1 if gradient_contrast >= self.cfg.GRADIENT_CONTRAST_MIN else 0)
        conf = min(0.98, 0.5 + intact * 0.1)
        return VoteResult("viable", conf, "rule_based")


# ===========================================================================
# Classifier 2 — CNN (MobileNetV2)
# ===========================================================================

class CNNClassifier:
    """
    Loads ev_viability_model.h5 and classifies cropped particle images.
    """

    def __init__(self, cfg: TEMConfig):
        self.cfg   = cfg
        self.model = None
        self._load_model()

    def _load_model(self):
        if not TF_AVAILABLE:
            logger.warning("CNN: TensorFlow not available.")
            return
        if not os.path.exists(self.cfg.CNN_MODEL_PATH):
            logger.warning(f"CNN: Model not found at {self.cfg.CNN_MODEL_PATH}")
            return
        try:
            self.model = keras.models.load_model(self.cfg.CNN_MODEL_PATH)
            logger.info(f"CNN: Loaded model from {self.cfg.CNN_MODEL_PATH}")
        except Exception as e:
            logger.error(f"CNN: Failed to load model — {e}")

    def classify(self, cropped_bgr: np.ndarray) -> VoteResult:
        if self.model is None:
            return VoteResult("needs_review", 0.5, "cnn")

        try:
            # Preprocess — match training pipeline
            img = cv2.resize(cropped_bgr, (self.cfg.CNN_IMG_SIZE, self.cfg.CNN_IMG_SIZE))
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            img = img.astype("float32") / 255.0
            img = np.expand_dims(img, axis=0)    # (1, 128, 128, 3)

            prob = float(self.model.predict(img, verbose=0)[0][0])

            # prob > 0.5 → viable (label=1), else non_viable (label=0)
            if prob > 0.5:
                conf = prob
                if conf < self.cfg.CNN_CONFIDENCE_MIN:
                    return VoteResult("needs_review", conf, "cnn")
                return VoteResult("viable", conf, "cnn")
            else:
                conf = 1.0 - prob
                if conf < self.cfg.CNN_CONFIDENCE_MIN:
                    return VoteResult("needs_review", conf, "cnn")
                return VoteResult("non_viable", conf, "cnn")

        except Exception as e:
            logger.error(f"CNN inference error: {e}")
            return VoteResult("needs_review", 0.5, "cnn")


# ===========================================================================
# Classifier 3 — Claude Vision via AWS Bedrock
# ===========================================================================

CLAUDE_SYSTEM_PROMPT = """You are an expert in Transmission Electron Microscopy (TEM) 
analysis of Extracellular Vesicles (EVs) and exosomes.

Your ONLY job is to assess membrane integrity. 

RULES (from domain expert):
- VIABLE: membrane forms a complete, continuous closed boundary. 
  Shape does NOT matter — oval, elongated, cup-shaped, crown = all VIABLE 
  if membrane is intact.
- NON_VIABLE: membrane is broken, ruptured, leaking, split, or has huge gaps.
- NEEDS_REVIEW: very elongated particles or overlapping particles where 
  you cannot clearly determine membrane integrity.

Respond ONLY with valid JSON. No explanation outside the JSON.
Format:
{
  "classification": "viable" | "non_viable" | "needs_review",
  "confidence": 0.0-1.0,
  "reason": "one sentence explanation"
}"""

CLAUDE_USER_PROMPT = """Analyze this cropped TEM image of a single EV/exosome particle.
Assess ONLY the membrane integrity.
Is the outer membrane boundary complete and continuous?
Respond with JSON only."""


class ClaudeVisionClassifier:
    """
    Sends cropped particle image to Claude via AWS Bedrock Converse API.
    Uses AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY from environment.
    """

    def __init__(self, cfg: TEMConfig):
        self.cfg    = cfg
        self.client = None
        self._init_client()

    def _init_client(self):
        if not self.cfg.AWS_ACCESS_KEY_ID or not self.cfg.AWS_SECRET_ACCESS_KEY:
            logger.warning("Claude Vision: AWS credentials not set. "
                           "Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY.")
            return
        try:
            self.client = boto3.client(
                service_name          = "bedrock-runtime",
                region_name           = self.cfg.AWS_REGION,
                aws_access_key_id     = self.cfg.AWS_ACCESS_KEY_ID,
                aws_secret_access_key = self.cfg.AWS_SECRET_ACCESS_KEY,
            )
            logger.info("Claude Vision: AWS Bedrock client initialised.")
        except Exception as e:
            logger.error(f"Claude Vision: Failed to init Bedrock client — {e}")

    def classify(self, cropped_bgr: np.ndarray) -> VoteResult:
        if self.client is None:
            return VoteResult("needs_review", 0.5, "claude_vision")

        try:
            # Encode cropped image as base64 PNG
            _, buf     = cv2.imencode(".png", cropped_bgr)
            img_b64    = base64.b64encode(buf.tobytes()).decode("utf-8")

            response = self.client.converse(
                modelId = self.cfg.BEDROCK_MODEL_ID,
                system  = [{"text": CLAUDE_SYSTEM_PROMPT}],
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {
                                "image": {
                                    "format": "png",
                                    "source": {"bytes": buf.tobytes()}
                                }
                            },
                            {"text": CLAUDE_USER_PROMPT}
                        ]
                    }
                ],
                inferenceConfig = {
                    "maxTokens":   self.cfg.BEDROCK_MAX_TOKENS,
                    "temperature": 0.1,    # low temperature = more consistent
                }
            )

            raw_text = response["output"]["message"]["content"][0]["text"]
            parsed   = self._parse_response(raw_text)
            return VoteResult(
                parsed.get("classification", "needs_review"),
                float(parsed.get("confidence", 0.5)),
                "claude_vision"
            )

        except ClientError as e:
            logger.error(f"Claude Vision: Bedrock API error — {e}")
            return VoteResult("needs_review", 0.5, "claude_vision")
        except Exception as e:
            logger.error(f"Claude Vision: Unexpected error — {e}")
            return VoteResult("needs_review", 0.5, "claude_vision")

    @staticmethod
    def _parse_response(text: str) -> dict:
        """Extract JSON from Claude's response robustly."""
        try:
            # Try direct parse
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass
        try:
            # Extract JSON block if wrapped in markdown
            start = text.find("{")
            end   = text.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
        except Exception:
            pass
        return {"classification": "needs_review", "confidence": 0.5,
                "reason": "Could not parse Claude response"}


# ===========================================================================
# Majority Vote
# ===========================================================================

def majority_vote(votes: List[VoteResult], cnn_weight: int = 2) -> Tuple[str, float, str]:
    """
    Weighted majority vote. CNN counts as 2 votes, others as 1.
    Claude Vision votes with confidence=0.50 are treated as abstain (API failed).
    If all active voters disagree → needs_review.
    Returns (classification, avg_confidence, summary).
    """
    # Filter out abstaining votes (Claude failed = confidence exactly 0.5)
    active_votes = [v for v in votes
                    if not (v.source == "claude_vision" and v.confidence == 0.5)]

    vote_pool = active_votes if active_votes else votes

    counts = {"viable": 0, "non_viable": 0, "needs_review": 0}
    for v in vote_pool:
        cls = v.classification if v.classification in counts else "needs_review"
        weight = cnn_weight if v.source == "cnn" else 1
        counts[cls] += weight

    winner    = max(counts, key=counts.get)
    win_count = counts[winner]

    if win_count == 1:
        winner    = "needs_review"
        win_count = 0

    winning_votes = [v for v in vote_pool
                     if v.classification == winner or winner == "needs_review"]
    avg_conf = np.mean([v.confidence for v in winning_votes]) if winning_votes else 0.5

    claude_note = "claude=abstain" if len(active_votes) < len(votes) else \
                  f"claude={votes[2].classification}({votes[2].confidence:.2f})"

    summary = (
        f"rule_based={votes[0].classification}({votes[0].confidence:.2f}) | "
        f"cnn={votes[1].classification}({votes[1].confidence:.2f}) | "
        f"{claude_note} | "
        f"vote={winner}({win_count}/{len(vote_pool)})"
    )
    return winner, float(avg_conf), summary


# ===========================================================================
# Main analyser
# ===========================================================================

class TEMAnalyzer:
    """
    Full pipeline:
      Detection (OpenCV) → Three classifiers → Majority vote → Annotated image
    """

    COLOUR = {
        "viable":       (0,   200,  0),    # green
        "non_viable":   (0,   0,    220),  # red   (BGR)
        "needs_review": (0,   200,  220),  # yellow (BGR)
    }
    OUTLINE_COLOUR = (200, 100, 0)          # blue outline

    def __init__(self, config: TEMConfig = None):
        self.cfg     = config or TEMConfig()
        self.rule    = RuleBasedClassifier(self.cfg)
        self.cnn     = CNNClassifier(self.cfg)
        self.claude  = ClaudeVisionClassifier(self.cfg)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(self, image_bgr: np.ndarray) -> AnalysisResult:
        gray         = self._to_gray(image_bgr)
        preprocessed = self._preprocess(gray)
        centers      = self._detect_blobs(preprocessed)
        label_map    = self._watershed_segment(preprocessed, centers)
        particles    = self._process_particles(image_bgr, gray, preprocessed, label_map)
        annotated    = self._draw_results(image_bgr, particles)
        detection    = self._draw_detection_only(image_bgr, particles)

        viable     = [p for p in particles if p.classification == "viable"]
        non_viable = [p for p in particles if p.classification == "non_viable"]
        review     = [p for p in particles if p.classification == "needs_review"]
        total      = len(particles)

        return AnalysisResult(
            total_detected   = total,
            viable_count     = len(viable),
            non_viable_count = len(non_viable),
            review_count     = len(review),
            viable_pct       = (len(viable) / total * 100) if total else 0.0,
            particles        = particles,
            annotated_image  = annotated,
            detection_image  = detection,
        )

    # ------------------------------------------------------------------
    # Steps 1-2: Preprocessing
    # ------------------------------------------------------------------

    def _to_gray(self, img):
        return img if len(img.shape) == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    def _preprocess(self, gray):
        blurred = cv2.GaussianBlur(gray, (0, 0), self.cfg.GAUSSIAN_SIGMA)
        clahe   = cv2.createCLAHE(
            clipLimit    = self.cfg.CLAHE_CLIP,
            tileGridSize = (self.cfg.CLAHE_TILE, self.cfg.CLAHE_TILE)
        )
        return clahe.apply(blurred)

    # ------------------------------------------------------------------
    # Step 3: Blob detection — one centre per EV
    # ------------------------------------------------------------------

    def _detect_blobs(self, preprocessed):
        img_f  = preprocessed.astype(np.float32) / 255.0
        blobs  = blob_log(img_f,
                          min_sigma=self.cfg.BLOB_MIN_SIGMA,
                          max_sigma=self.cfg.BLOB_MAX_SIGMA,
                          num_sigma=self.cfg.BLOB_NUM_SIGMA,
                          threshold=self.cfg.BLOB_THRESHOLD)
        if blobs is None or len(blobs) == 0:
            blobs = blob_log(1.0 - img_f,
                             min_sigma=self.cfg.BLOB_MIN_SIGMA,
                             max_sigma=self.cfg.BLOB_MAX_SIGMA,
                             num_sigma=self.cfg.BLOB_NUM_SIGMA,
                             threshold=self.cfg.BLOB_THRESHOLD)
        result = []
        for b in (blobs if blobs is not None else []):
            r, c, sigma = b
            radius = sigma * np.sqrt(2)
            diam   = radius * 2
            if self.cfg.MIN_DIAMETER_PX <= diam <= self.cfg.MAX_DIAMETER_PX:
                result.append((int(r), int(c), float(radius)))
        return result

    # ------------------------------------------------------------------
    # Step 4: Watershed segmentation
    # ------------------------------------------------------------------

    def _watershed_segment(self, preprocessed, centers):
        h, w    = preprocessed.shape
        markers = np.zeros((h, w), dtype=np.int32)
        for idx, (r, c, radius) in enumerate(centers, start=1):
            rr = int(np.clip(r, 0, h - 1))
            cc = int(np.clip(c, 0, w - 1))
            cv2.circle(markers, (cc, rr), max(1, int(radius * 0.3)), idx, -1)
        if np.max(markers) == 0:
            return np.zeros((h, w), dtype=np.int32)
        gradient = cv2.morphologyEx(
            preprocessed,
            cv2.MORPH_GRADIENT,
            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        )
        return watershed(gradient, markers, compactness=0.001)

    # ------------------------------------------------------------------
    # Step 5: Feature extraction + three classifiers + majority vote
    # ------------------------------------------------------------------

    def _process_particles(self, image_bgr, gray, preprocessed, label_map):
        particles = []
        edge_map  = cv2.Canny(preprocessed, 30, 80)
        props     = regionprops(label_map, intensity_image=gray)

        for prop in props:
            diam = 2 * np.sqrt(prop.area / np.pi)
            if diam < self.cfg.MIN_DIAMETER_PX or diam > self.cfg.MAX_DIAMETER_PX:
                continue

            mask = (label_map == prop.label).astype(np.uint8) * 255
            contours, _ = cv2.findContours(
                mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            if not contours:
                continue
            contour = max(contours, key=cv2.contourArea)

            # --- geometry ---
            major        = max(prop.major_axis_length, 1)
            minor        = max(prop.minor_axis_length, 1)
            aspect_ratio = major / minor
            eccentricity = prop.eccentricity
            solidity     = prop.solidity

            # --- membrane metrics ---
            edge_cov   = self._edge_coverage(mask, edge_map)
            grad_cont  = self._gradient_contrast(gray, mask)
            mem_cont   = self._membrane_continuous(mask, edge_map, edge_cov)

            # --- crop particle for CNN and Claude ---
            cropped    = self._crop_particle(image_bgr, mask)

            # --- run three classifiers ---
            vote_rule  = self.rule.classify(
                solidity, eccentricity, edge_cov, grad_cont, mem_cont
            )
            vote_cnn   = self.cnn.classify(cropped)
            vote_claude = self.claude.classify(cropped)

            votes      = [vote_rule, vote_cnn, vote_claude]
            final_cls, final_conf, summary = majority_vote(votes)

            cy, cx = prop.centroid
            particles.append(EVParticle(
                particle_id         = prop.label,
                classification      = final_cls,
                confidence          = final_conf,
                votes               = votes,
                vote_summary        = summary,
                center_x            = cx,
                center_y            = cy,
                area_px             = prop.area,
                diameter_px         = diam,
                aspect_ratio        = aspect_ratio,
                eccentricity        = eccentricity,
                solidity            = solidity,
                edge_coverage       = edge_cov,
                gradient_contrast   = grad_cont,
                membrane_continuous = mem_cont,
                contour             = contour,
                cropped_image       = cropped,
            ))

        logger.info(
            f"Processed {len(particles)} particles. "
            f"Viable={sum(1 for p in particles if p.classification=='viable')} "
            f"NonViable={sum(1 for p in particles if p.classification=='non_viable')} "
            f"Review={sum(1 for p in particles if p.classification=='needs_review')}"
        )
        return particles

    # ------------------------------------------------------------------
    # Membrane integrity helpers
    # ------------------------------------------------------------------

    def _edge_coverage(self, mask, edge_map):
        k        = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        boundary = cv2.subtract(cv2.dilate(mask, k), cv2.erode(mask, k))
        bp       = np.count_nonzero(boundary)
        if bp == 0:
            return 0.0
        return np.count_nonzero(cv2.bitwise_and(boundary, edge_map)) / bp

    def _gradient_contrast(self, gray, mask):
        k      = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        outer  = cv2.subtract(cv2.dilate(mask, k, iterations=2), mask)
        inside = gray[mask > 0]
        outside = gray[outer > 0]
        if len(inside) == 0 or len(outside) == 0:
            return 0.0
        return float(abs(np.mean(inside) - np.mean(outside)))

    def _membrane_continuous(self, mask, edge_map, edge_cov):
        n, _ = cv2.connectedComponents(mask)
        if n > 2:
            return False
        if edge_cov < self.cfg.EDGE_COVERAGE_VIABLE:
            return False
        contours, _ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        if not contours:
            return False
        c    = max(contours, key=cv2.contourArea)
        hull = cv2.convexHull(c)
        hm   = np.zeros_like(mask)
        cv2.drawContours(hm, [hull], -1, 255, -1)
        ha   = np.count_nonzero(hm)
        return (np.count_nonzero(mask) / ha >= 0.45) if ha > 0 else False

    def _crop_particle(self, image_bgr, mask, padding=10):
        """Crop bounding box of particle with padding."""
        coords = cv2.findNonZero(mask)
        if coords is None:
            return image_bgr
        x, y, w, h = cv2.boundingRect(coords)
        ih, iw     = image_bgr.shape[:2]
        x1 = max(0, x - padding)
        y1 = max(0, y - padding)
        x2 = min(iw, x + w + padding)
        y2 = min(ih, y + h + padding)
        return image_bgr[y1:y2, x1:x2]

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def _draw_results(self, image_bgr, particles):
        output  = image_bgr.copy()
        overlay = image_bgr.copy()
        for p in particles:
            if p.contour is None:
                continue
            colour = self.COLOUR.get(p.classification, (128, 128, 128))
            cv2.drawContours(overlay, [p.contour], -1, colour, -1)
            cv2.drawContours(output,  [p.contour], -1, colour, 2)
        cv2.addWeighted(overlay, 0.35, output, 0.65, 0, output)
        for p in particles:
            lbl = {"viable": "V", "non_viable": "NV", "needs_review": "R"}.get(
                p.classification, "?"
            )
            cv2.putText(
                output, lbl,
                (int(p.center_x) - 6, int(p.center_y) + 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.35,
                self.COLOUR.get(p.classification, (255, 255, 255)),
                1, cv2.LINE_AA
            )
        return output

    def _draw_detection_only(self, image_bgr, particles):
        output = image_bgr.copy()
        for p in particles:
            if p.contour is None:
                continue
            colour = (0, 0, 220) if p.classification == "non_viable" \
                     else self.OUTLINE_COLOUR
            cv2.drawContours(output, [p.contour], -1, colour, 1)
        return output


# ===========================================================================
# Drop-in API wrapper (compatible with existing main.py / FastAPI routes)
# ===========================================================================

def analyze_image(image_bgr: np.ndarray, config: TEMConfig = None) -> dict:
    """
    Drop-in wrapper for FastAPI routes.

    Returns:
    {
        "total":          int,
        "viable":         int,
        "non_viable":     int,
        "needs_review":   int,
        "viable_pct":     float,
        "particles":      [ {id, classification, confidence, votes, ...} ],
        "annotated_image": np.ndarray (BGR),
        "detection_image": np.ndarray (BGR),
    }
    """
    analyzer = TEMAnalyzer(config)
    result   = analyzer.analyze(image_bgr)

    return {
        "total":          result.total_detected,
        "viable":         result.viable_count,
        "non_viable":     result.non_viable_count,
        "needs_review":   result.review_count,
        "viable_pct":     round(result.viable_pct, 2),
        "particles": [
            {
                "id":                p.particle_id,
                "classification":    p.classification,
                "confidence":        round(p.confidence, 3),
                "votes": {
                    "rule_based":    p.votes[0].classification,
                    "cnn":           p.votes[1].classification,
                    "claude_vision": p.votes[2].classification,
                },
                "vote_summary":      p.vote_summary,
                "center":            (round(p.center_x, 1), round(p.center_y, 1)),
                "diameter_px":       round(p.diameter_px, 1),
                "aspect_ratio":      round(p.aspect_ratio, 3),
                "eccentricity":      round(p.eccentricity, 3),
                "solidity":          round(p.solidity, 3),
                "edge_coverage":     round(p.edge_coverage, 3),
                "gradient_contrast": round(p.gradient_contrast, 1),
                "membrane_intact":   p.membrane_continuous,
            }
            for p in result.particles
        ],
        "annotated_image": result.annotated_image,
        "detection_image": result.detection_image,
    }


# ===========================================================================
# Quick test — python tem_analyzer.py your_image.png
# ===========================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python tem_analyzer.py <image_path>")
        print("       AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY must be set.")
        sys.exit(1)

    path = sys.argv[1]
    if not os.path.exists(path):
        print(f"File not found: {path}")
        sys.exit(1)

    img    = cv2.imread(path)
    result = analyze_image(img)

    print(f"\n{'='*55}")
    print(f"  TEM EV Analysis — {os.path.basename(path)}")
    print(f"{'='*55}")
    print(f"  Total detected : {result['total']}")
    print(f"  Viable         : {result['viable']}  ({result['viable_pct']:.1f}%)")
    print(f"  Non-viable     : {result['non_viable']}")
    print(f"  Needs review   : {result['needs_review']}")
    print(f"{'='*55}")
    print("\nPer-particle votes:")
    for p in result["particles"][:5]:   # show first 5
        print(f"  #{p['id']:3d}  {p['classification']:12s}  {p['vote_summary']}")
    if len(result["particles"]) > 5:
        print(f"  ... and {len(result['particles'])-5} more")

    base = os.path.splitext(path)[0]
    cv2.imwrite(f"{base}_annotated.png", result["annotated_image"])
    cv2.imwrite(f"{base}_detection.png", result["detection_image"])
    print(f"\nSaved: {base}_annotated.png")
 print(f"Saved: {base}_detection.png”)








(venv_tf) abcd@abcds-MacBook-Pro filescrmit_3methods % python -c "
import sys, os, cv2, glob
sys.path.insert(0, '.')
import tem_analyzer_colourcode_predictions as ta
ta.TEMConfig.BLOB_THRESHOLD  = 0.08
ta.TEMConfig.MIN_DIAMETER_PX = 30
os.makedirs('results/test_annotated', exist_ok=True)
for f in sorted(glob.glob('Training Data/test*.png')):
    if 'annotated' in f or 'detection' in f or 'small' in f: continue
    img = cv2.imread(f)
    if img is None: continue
    r = ta.analyze_image(img)
    name = os.path.basename(f).replace('.png','')
    cv2.imwrite('results/test_annotated/' + name + '_annotated.png', r['annotated_image'])
    print(name + ': ' + str(r['total']) + ' particles')
"
INFO:tem_analyzer_colourcode_predictions:CNN: Loaded model from ev_viability_best_model.h5
INFO:botocore.tokens:Found token in environment variables.
INFO:tem_analyzer_colourcode_predictions:Claude Vision: AWS Bedrock client initialised.
INFO:tem_analyzer_colourcode_predictions:Processed 1 particles. Viable=0 NonViable=0 Review=1
test1: 1 particles
INFO:tem_analyzer_colourcode_predictions:CNN: Loaded model from ev_viability_best_model.h5
INFO:botocore.tokens:Found token in environment variables.
INFO:tem_analyzer_colourcode_predictions:Claude Vision: AWS Bedrock client initialised.
INFO:tem_analyzer_colourcode_predictions:Processed 1 particles. Viable=0 NonViable=1 Review=0
test2: 1 particles
INFO:tem_analyzer_colourcode_predictions:CNN: Loaded model from ev_viability_best_model.h5
INFO:botocore.tokens:Found token in environment variables.
INFO:tem_analyzer_colourcode_predictions:Claude Vision: AWS Bedrock client initialised.
INFO:tem_analyzer_colourcode_predictions:Processed 1 particles. Viable=1 NonViable=0 Review=0
test3: 1 particles
INFO:tem_analyzer_colourcode_predictions:CNN: Loaded model from ev_viability_best_model.h5
INFO:botocore.tokens:Found token in environment variables.
INFO:tem_analyzer_colourcode_predictions:Claude Vision: AWS Bedrock client initialised.
INFO:tem_analyzer_colourcode_predictions:Processed 2 particles. Viable=0 NonViable=2 Review=0
test4 : 2 particles
INFO:tem_analyzer_colourcode_predictions:CNN: Loaded model from ev_viability_best_model.h5
INFO:botocore.tokens:Found token in environment variables.
INFO:tem_analyzer_colourcode_predictions:Claude Vision: AWS Bedrock client initialised.
WARNING:tensorflow:5 out of the last 6 calls to <function Model.make_predict_function.<locals>.predict_function at 0x19190f560> triggered tf.function retracing. Tracing is expensive and the excessive number of tracings could be due to (1) creating @tf.function repeatedly in a loop, (2) passing tensors with different shapes, (3) passing Python objects instead of tensors. For (1), please define your @tf.function outside of the loop. For (2), @tf.function has reduce_retracing=True option that can avoid unnecessary retracing. For (3), please refer to https://www.tensorflow.org/guide/function#controlling_retracing and https://www.tensorflow.org/api_docs/python/tf/function for  more details.
WARNING:tensorflow:5 out of the last 6 calls to <function Model.make_predict_function.<locals>.predict_function at 0x19190f560> triggered tf.function retracing. Tracing is expensive and the excessive number of tracings could be due to (1) creating @tf.function repeatedly in a loop, (2) passing tensors with different shapes, (3) passing Python objects instead of tensors. For (1), please define your @tf.function outside of the loop. For (2), @tf.function has reduce_retracing=True option that can avoid unnecessary retracing. For (3), please refer to https://www.tensorflow.org/guide/function#controlling_retracing and https://www.tensorflow.org/api_docs/python/tf/function for  more details.
INFO:tem_analyzer_colourcode_predictions:Processed 8 particles. Viable=0 NonViable=8 Review=0
test5: 8 particles
INFO:tem_analyzer_colourcode_predictions:CNN: Loaded model from ev_viability_best_model.h5
INFO:botocore.tokens:Found token in environment variables.
INFO:tem_analyzer_colourcode_predictions:Claude Vision: AWS Bedrock client initialised.
INFO:tem_analyzer_colourcode_predictions:Processed 4 particles. Viable=0 NonViable=4 Review=0
test6: 4 particles
INFO:tem_analyzer_colourcode_predictions:CNN: Loaded model from ev_viability_best_model.h5
INFO:botocore.tokens:Found token in environment variables.
INFO:tem_analyzer_colourcode_predictions:Claude Vision: AWS Bedrock client initialised.
INFO:tem_analyzer_colourcode_predictions:Processed 3 particles. Viable=1 NonViable=2 Review=0
test7: 3 particles
(venv_tf) abcd@abcds-MacBook-Pro filescrmit_3methods % open results/test_annotated/
(venv_tf) abcd@abcds-MacBook-Pro filescrmit_3methods % 









Image	Detected	Result
test1	1	needs_review ⚠️
test2	1	non_viable ✅
test3	1	viable ✅
test4	2	non_viable ✅
test5	8	non_viable ✅ (over-detected, but correct class)
test6	4	non_viable ✅ (over-detected, but correct class)
test7	3	mixed (1 viable ❌, 2 non_viable)


