import os
import json
import cv2
import numpy as np
import boto3


DEFAULT_SHAPE_RULES = [
    {"condition": "circularity > 0.75", "color": "green"},
    {"condition": "else", "color": "red"},
]


def get_bedrock_client():
    aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_region = os.getenv("AWS_REGION", "us-east-1")

    if not aws_access_key or not aws_secret_key:
        return None

    return boto3.client(
        "bedrock-runtime",
        region_name=aws_region,
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key,
    )


def get_shape_classification_rules(instructions: str = "", use_ai_rules: bool = False):
    if not use_ai_rules or not instructions or not instructions.strip():
        return DEFAULT_SHAPE_RULES

    client = get_bedrock_client()
    if client is None:
        return DEFAULT_SHAPE_RULES

    prompt = f"""
You are a computer vision rule engine.

DEFAULT rules already in place:
- circularity > 0.75 -> GREEN
- circularity <= 0.75 -> RED

The client wants to add or override on top of these defaults:
\"\"\"{instructions}\"\"\"

Each shape has these features:
- circularity : 4*pi*area/perimeter^2
- solidity    : area / convex_hull_area
- convexity   : convex_perimeter / perimeter

Return ONLY a JSON array of rules evaluated top-to-bottom.
Each rule must have:
- "condition"
- "color" ("green" or "red")

Always end with an else rule.
No extra text.
"""

    try:
        payload = {"messages": [{"role": "user", "content": prompt}]}
        response = client.invoke_model(
            modelId="mistral.mistral-large-2402-v1:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload),
        )
        result = json.loads(response["body"].read())
        text = result["choices"][0]["message"]["content"].strip()
        text = text.replace("```json", "").replace("```", "").strip()
        rules = json.loads(text)

        if isinstance(rules, list) and len(rules) > 0:
            return rules

        return DEFAULT_SHAPE_RULES
    except Exception as e:
        print(f"[WARN] Bedrock rule generation failed: {e}")
        return DEFAULT_SHAPE_RULES


def apply_shape_rules(rules, circularity, solidity, convexity):
    color_map = {
        "green": (0, 255, 0),
        "red": (0, 0, 255),
    }

    for rule in rules:
        cond = rule.get("condition", "")
        color = rule.get("color", "red")

        if cond == "else":
            return color_map.get(color, (0, 0, 255))

        try:
            if eval(
                cond,
                {"__builtins__": {}},
                {
                    "circularity": circularity,
                    "solidity": solidity,
                    "convexity": convexity,
                },
            ):
                return color_map.get(color, (0, 0, 255))
        except Exception:
            continue

    return (0, 0, 255)


def extract_circle_from_contour(cnt):
    """
    Extract circle center and radius from a contour.
    Uses the equivalent circle concept: radius = sqrt(area / pi)
    Returns (center_x, center_y, radius_px) or None if invalid.
    """
    area = cv2.contourArea(cnt)
    if area <= 0:
        return None

    # Fit ellipse if possible for better center estimation
    if len(cnt) >= 5:
        try:
            ellipse = cv2.fitEllipse(cnt)
            (cx, cy), (minor_axis, major_axis), angle = ellipse
            radius = (minor_axis + major_axis) / 4.0
            return float(cx), float(cy), float(radius)
        except Exception:
            pass

    # Fallback: use moments for centroid
    M = cv2.moments(cnt)
    if M["m00"] > 0:
        cx = M["m10"] / M["m00"]
        cy = M["m01"] / M["m00"]
        radius = np.sqrt(area / np.pi)
        return float(cx), float(cy), float(radius)

    return None


def compute_shape_features(cnt, gray):
    area = cv2.contourArea(cnt)
    perimeter = cv2.arcLength(cnt, True)

    if area <= 0 or perimeter <= 0:
        return None

    circularity = 4 * np.pi * area / (perimeter * perimeter)

    hull = cv2.convexHull(cnt)
    hull_area = cv2.contourArea(hull)
    hull_perimeter = cv2.arcLength(hull, True)

    solidity = area / hull_area if hull_area > 0 else 1.0
    convexity = hull_perimeter / perimeter if perimeter > 0 else 1.0

    mask = np.zeros(gray.shape, dtype=np.uint8)
    cv2.fillPoly(mask, [cnt], 255)
    mean_gray = float(cv2.mean(gray, mask=mask)[0])
    depth = round(mean_gray / 255.0, 4)

    return {
        "area": round(float(area), 3),
        "perimeter": round(float(perimeter), 3),
        "circularity": round(float(circularity), 6),
        "solidity": round(float(solidity), 6),
        "convexity": round(float(convexity), 6),
        "depth": depth,
    }


def resolve_feedback_for_particle(feedbacks, idx):
    for fb in feedbacks or []:
        if int(fb.get("matched_idx", -1)) == int(idx):
            action = str(fb.get("action", "")).lower()
            label = fb.get("label")

            if action == "skip":
                return None, True, label
            if action == "green":
                return (0, 255, 0), False, label
            if action == "red":
                return (0, 0, 255), False, label

    return None, False, None


def find_nearest_particle(cx, cy, particles):
    """
    Find nearest particle to point (cx, cy).
    Works with both circle-based (center_x, center_y) and bbox-based particles.
    """
    best = None
    best_dist = float("inf")

    for p in particles:
        if p.get("color_name") == "skipped":
            continue

        # Try circle-based coordinates first (preferred)
        if "center_x" in p and "center_y" in p:
            pcx = float(p["center_x"])
            pcy = float(p["center_y"])
            radius = float(p.get("radius_px", 10))
            d = (pcx - cx) ** 2 + (pcy - cy) ** 2

            # Reduce distance if click is inside circle
            if d <= radius ** 2:
                d -= 1e9
        else:
            # Fallback to bbox-based coordinates
            bbox = p.get("bbox", {})
            x = bbox.get("x", 0)
            y = bbox.get("y", 0)
            w = bbox.get("w", 0)
            h = bbox.get("h", 0)

            pcx = x + (w / 2)
            pcy = y + (h / 2)
            d = (pcx - cx) ** 2 + (pcy - cy) ** 2

            if x <= cx <= x + w and y <= cy <= y + h:
                d -= 1e9

        if d < best_dist:
            best_dist = d
            best = p

    return best


def run_shape_classification_pipeline(
    img_bgr,
    rules,
    feedbacks=None,
    min_area=300,
    close_kernel=5,
    close_iterations=2,
    nm_per_pixel: float = 0.5,
    min_diameter_nm: float = 30.0,
):
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    overlay = img_bgr.copy()
    if nm_per_pixel is None:
        nm_per_pixel = 0.5

    smooth = cv2.bilateralFilter(gray, 9, 75, 75)

    _, mask = cv2.threshold(
        smooth,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU,
    )

    if np.mean(mask) > 127:
        mask = cv2.bitwise_not(mask)

    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask)

    clean_mask = np.zeros_like(mask)
    for i in range(1, num_labels):
        area = stats[i, cv2.CC_STAT_AREA]
        if area > int(min_area):
            clean_mask[labels == i] = 255

    kernel = np.ones((int(close_kernel), int(close_kernel)), np.uint8)
    clean_mask = cv2.morphologyEx(
        clean_mask,
        cv2.MORPH_CLOSE,
        kernel,
        iterations=int(close_iterations),
    )

    contours, _ = cv2.findContours(
        clean_mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    filtered_mask = np.zeros_like(clean_mask)
    particles = []

    for idx, cnt in enumerate(contours):
        features = compute_shape_features(cnt, gray)
        if features is None:
            continue

        # Extract circle parameters from contour
        circle_data = extract_circle_from_contour(cnt)
        if circle_data is None:
            continue

        center_x, center_y, radius_px = circle_data
        radius_px = max(1.0, radius_px)
        diameter_nm = 2.0 * radius_px * float(nm_per_pixel)
        if diameter_nm < float(min_diameter_nm):
            continue

        x, y, w, h = cv2.boundingRect(cnt)

        forced_color, skip, note = resolve_feedback_for_particle(feedbacks, idx)
        if skip:
            cv2.circle(
                filtered_mask,
                (int(center_x), int(center_y)),
                int(radius_px),
                255,
                thickness=-1,
                lineType=cv2.LINE_AA,
            )
            particles.append(
                {
                    "idx": idx,
                    "center_x": center_x,
                    "center_y": center_y,
                    "radius_px": radius_px,
                    "diameter_nm": round(diameter_nm, 2),
                    "bbox": {"x": int(x), "y": int(y), "w": int(w), "h": int(h)},
                    "features": features,
                    "color_name": "skipped",
                    "feedback": note,
                }
            )
            continue

        if forced_color is None:
            fill_color = apply_shape_rules(
                rules,
                features["circularity"],
                features["solidity"],
                features["convexity"],
            )
            feedback_note = None
        else:
            fill_color = forced_color
            feedback_note = note

        cv2.circle(
            filtered_mask,
            (int(center_x), int(center_y)),
            int(radius_px),
            255,
            thickness=-1,
            lineType=cv2.LINE_AA,
        )

        color_name = "green" if fill_color == (0, 255, 0) else "red"

        particles.append(
            {
                "idx": idx,
                "center_x": center_x,
                "center_y": center_y,
                "radius_px": radius_px,
                "diameter_nm": round(diameter_nm, 2),
                "bbox": {"x": int(x), "y": int(y), "w": int(w), "h": int(h)},
                "features": features,
                "color_name": color_name,
                "feedback": feedback_note,
            }
        )

    return overlay, filtered_mask, particles


# ---------------------------------------------------------------------------
# Natural-language feedback → structured action
# Adapted from app.py (Charmi, 2025-05)
# ---------------------------------------------------------------------------

def parse_feedback_text(text: str, current_status: str = "Intact") -> dict:
    """
    Convert free-text user feedback into a structured action dict.

    Returns:
        {"action": "green" | "red" | "skip", "note": <original text>}

    Strategy:
      1. Fast keyword match — no API call for unambiguous phrases.
      2. Fallback to Mistral via AWS Bedrock for ambiguous input.
      3. Final fallback: preserve current classification.
    """
    t = text.lower()

    # --- fast keyword path ---
    if any(w in t for w in ["ignore", "skip", "remove", "hide", "noise", "artifact"]):
        return {"action": "skip", "note": text}

    if any(w in t for w in [
        "non-intact", "non intact", "broken", "damage", "bad",
        "wrong", "not intact", "not good",
    ]):
        return {"action": "red", "note": text}

    if any(w in t for w in [
        "intact", "green", "fine", "good", "correct",
        "keep", "this is intact", "make it green",
    ]):
        return {"action": "green", "note": text}

    # --- Bedrock/Mistral fallback for ambiguous phrasing ---
    try:
        client = get_bedrock_client()
        if client is None:
            raise ValueError("AWS credentials not configured")

        prompt = (
            f'Particle currently: "{current_status}". User says: "{text}". '
            f'Return ONLY JSON: {{"action":"green"|"red"|"skip","note":"brief summary"}} '
            f"green=intact, red=non-intact, skip=ignore/remove."
        )
        payload = {"messages": [{"role": "user", "content": prompt}]}
        response = client.invoke_model(
            modelId="mistral.mistral-large-2402-v1:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload),
        )
        raw = json.loads(response["body"].read())
        content = raw["choices"][0]["message"]["content"].strip()
        content = content.replace("```json", "").replace("```", "").strip()
        return json.loads(content)

    except Exception as e:
        print(f"[WARN] parse_feedback_text Bedrock call failed: {e}")
        # Preserve the current classification as the safest default
        default_action = "green" if current_status.lower() == "intact" else "red"
        return {"action": default_action, "note": text}