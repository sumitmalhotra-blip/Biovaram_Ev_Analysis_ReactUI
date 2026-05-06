#!/usr/bin/env python3
"""
Nova-based EV Particle Detector
================================
Uses Amazon Nova Lite vision model to detect EV particles in TEM images.
Returns bounding boxes which are used instead of blob detection + watershed.

Drop-in replacement: call detect_particles_nova(image_bgr, client) to get
a list of (x, y, w, h) bounding boxes for each detected particle.
"""

import cv2
import json
import base64
import logging
import numpy as np

logger = logging.getLogger(__name__)

NOVA_DETECTION_PROMPT = """You are an expert in Transmission Electron Microscopy (TEM) analysis of Extracellular Vesicles (EVs).

Look at this TEM image. Your job is to detect and locate ALL visible EV particles (vesicles/exosomes).

DETECTION RULES:
- Each EV appears as a roughly circular/oval dark-rimmed structure
- Do NOT split one EV into multiple detections — one vesicle = one bounding box
- Do NOT detect internal structures, texture, or background grain as separate particles
- If the image shows ONE large EV, return ONE bounding box covering it fully
- Include ALL EVs visible in the image, even partial ones at edges
- An elongated or deformed particle is still ONE particle — do not split it

Return ONLY a JSON array of bounding boxes. Each box has:
  x: left edge (pixels from left)
  y: top edge (pixels from top)
  w: width in pixels
  h: height in pixels

Example response (2 particles found):
[
  {"x": 45, "y": 30, "w": 120, "h": 115},
  {"x": 200, "y": 80, "w": 95, "h": 100}
]

If NO particles found, return: []
Respond with ONLY the JSON array, nothing else."""


NOVA_CLASSIFICATION_PROMPT = """You are an expert in Transmission Electron Microscopy (TEM) analysis of Extracellular Vesicles (EVs).

Classify this cropped TEM image of a single EV particle as viable, non_viable, or needs_review.

VIABLE (structurally intact) if:
- Membrane is fully closed with no visible opening, break, or rim
- Particle forms a complete bounded object (not fragmented)
- Solidity is high — particle is not strongly concave
- No visible concavity or inward curvature in the boundary
- Outline is smooth and continuous without broken edges
- Aspect ratio is close to circular — not strongly elongated or deformed
- Appears as one coherent object, no internal fragmentation

NON-VIABLE (damaged/collapsed/artifact) if:
- Membrane is open or incomplete with a visible rim or break
- Cup-shaped or C-shaped morphology indicating collapse
- Clear concavity in the boundary (inward bending or indentation)
- Fragmented into multiple contours
- Extremely small — likely noise or stain artifact
- Strongly elongated or irregular indicating deformation
- Multiple internal edges detected inside the particle
- Background grain or uranyl acetate noise rather than a real vesicle
- When uncertain, label conservatively as non_viable

NEEDS_REVIEW if:
- Particle is borderline and cannot be confidently classified
- Severely overlapping with another particle making assessment impossible

Respond ONLY with valid JSON:
{
  "classification": "viable" | "non_viable" | "needs_review",
  "confidence": 0.0-1.0,
  "reason": "one sentence explanation"
}"""


def detect_particles_nova(image_bgr: np.ndarray, bedrock_client) -> list:
    """
    Use Nova vision to detect EV particles in a TEM image.
    Returns list of (x, y, w, h) tuples — one per detected particle.
    Falls back to empty list if Nova fails.
    """
    try:
        ih, iw = image_bgr.shape[:2]

        # Encode image as PNG bytes
        _, buf = cv2.imencode(".png", image_bgr)
        img_bytes = buf.tobytes()

        response = bedrock_client.converse(
            modelId="amazon.nova-lite-v1:0",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "image": {
                                "format": "png",
                                "source": {"bytes": img_bytes}
                            }
                        },
                        {"text": NOVA_DETECTION_PROMPT}
                    ]
                }
            ],
            inferenceConfig={
                "maxTokens": 500,
                "temperature": 0.1,
            }
        )

        raw = response["output"]["message"]["content"][0]["text"].strip()
        logger.info(f"Nova detection response: {raw[:200]}")

        # Parse JSON array
        boxes = _parse_boxes(raw, iw, ih)
        logger.info(f"Nova detected {len(boxes)} particles")
        return boxes

    except Exception as e:
        logger.error(f"Nova detection failed: {e}")
        return []


def _parse_boxes(text: str, img_w: int, img_h: int) -> list:
    """Parse Nova's JSON response into list of (x, y, w, h) tuples."""
    try:
        # Try direct parse
        data = json.loads(text)
    except json.JSONDecodeError:
        # Extract JSON array from text
        try:
            start = text.find("[")
            end   = text.rfind("]") + 1
            if start >= 0 and end > start:
                data = json.loads(text[start:end])
            else:
                logger.error("Nova: No JSON array found in response")
                return []
        except Exception:
            logger.error("Nova: Could not parse response as JSON")
            return []

    if not isinstance(data, list):
        return []

    boxes = []
    for item in data:
        try:
            x = int(item.get("x", 0))
            y = int(item.get("y", 0))
            w = int(item.get("w", 0))
            h = int(item.get("h", 0))

            # Clamp to image bounds
            x = max(0, min(x, img_w - 1))
            y = max(0, min(y, img_h - 1))
            w = max(10, min(w, img_w - x))
            h = max(10, min(h, img_h - y))

            # Skip tiny boxes (likely noise)
            if w < 20 or h < 20:
                continue

            boxes.append((x, y, w, h))
        except Exception:
            continue

    return boxes


def boxes_to_masks(image_bgr: np.ndarray, boxes: list) -> list:
    """
    Convert bounding boxes to (mask, contour, center_x, center_y) tuples.
    Each mask is a binary image with the ellipse region filled.
    """
    ih, iw = image_bgr.shape[:2]
    results = []

    for (x, y, w, h) in boxes:
        mask = np.zeros((ih, iw), dtype=np.uint8)
        cx   = x + w // 2
        cy   = y + h // 2
        # Draw filled ellipse as mask
        cv2.ellipse(mask, (cx, cy), (w // 2, h // 2), 0, 0, 360, 255, -1)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contour = max(contours, key=cv2.contourArea) if contours else None

        results.append({
            "mask":     mask,
            "contour":  contour,
            "center_x": float(cx),
            "center_y": float(cy),
            "x": x, "y": y, "w": w, "h": h,
        })

    return results
