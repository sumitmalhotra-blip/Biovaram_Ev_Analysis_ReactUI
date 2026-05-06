# tem_analyzer_ai.py
import cv2
import numpy as np
import base64
import json
from typing import List, Dict, Optional
import os
import asyncio
import httpx


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


class ClaudeAIAnalyzer:
    """AI-powered EV analyzer using Claude API."""

    def __init__(self, nm_per_pixel=0.5):
        self.nm_per_pixel = nm_per_pixel
        self.api_url = "https://api.anthropic.com/v1/messages"
        self.model = "claude-sonnet-4-20250514"

    def image_to_base64(self, image_path: str) -> Optional[str]:
        """Convert image to base64."""
        try:
            with open(image_path, 'rb') as f:
                return base64.b64encode(f.read()).decode('utf-8')
        except Exception as e:
            print(f"Error encoding image: {e}")
            return None

    def get_mime_type(self, image_path: str) -> str:
        """Get MIME type from file extension."""
        ext = os.path.splitext(image_path)[1].lower()
        return {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png', 
                'tif': 'image/tiff', 'tiff': 'image/tiff'}.get(ext.replace('.', ''), 'image/jpeg')

    async def analyze_with_claude_api(self, image_path: str, examples: List[Dict] = None) -> List[Dict]:
        """Call Claude API for image analysis."""
        img_b64 = self.image_to_base64(image_path)
        if not img_b64:
            return []

        content = []
        
        # Add examples if provided
        if examples:
            for idx, ex in enumerate(examples[:3]):
                ex_b64 = self.image_to_base64(ex["image_path"])
                if ex_b64:
                    content.extend([
                        {"type": "text", "text": f"Example {idx + 1} - Expert Labeled:"},
                        {"type": "image", "source": {"type": "base64", 
                         "media_type": self.get_mime_type(ex["image_path"]), "data": ex_b64}},
                        {"type": "text", "text": f"Labels:\n```json\n{json.dumps(ex['labels'], indent=2)}\n```"}
                    ])

        # Add main image
        content.extend([
            {"type": "text", "text": "Analyze this TEM image:"},
            {"type": "image", "source": {"type": "base64", 
             "media_type": self.get_mime_type(image_path), "data": img_b64}},
            {"type": "text", "text": """Identify EVs in this TEM image. Return ONLY valid JSON array:
[{"x": 234.5, "y": 123.8, "r": 15.2, "viability": "intact"}]

viability options: "intact" (clear membrane, good contrast), "not_intact" (damaged/irregular), "needs_review" (ambiguous)
Coordinates in pixels from top-left. r is radius in pixels."""}
        ])

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.api_url,
                    headers={"Content-Type": "application/json", "anthropic-version": "2023-06-01"},
                    json={"model": self.model, "max_tokens": 4000, "messages": [{"role": "user", "content": content}]}
                )
                
                if response.status_code != 200:
                    print(f"API Error: {response.status_code} - {response.text}")
                    return []

                result = response.json()
                text = result.get("content", [{}])[0].get("text", "")
                
                # Extract JSON from response
                if "```json" in text:
                    text = text.split("```json")[1].split("```")[0]
                elif "```" in text:
                    text = text.split("```")[1].split("```")[0]
                
                return json.loads(text.strip())
        except Exception as e:
            print(f"Claude API error: {e}")
            return []

    def analyze_image(self, image_path: str, example_images: List[Dict] = None) -> List[Dict]:
        """Synchronous wrapper for analyze_with_claude_api."""
        return asyncio.run(self.analyze_with_claude_api(image_path, example_images))

    def enrich_results(self, results: List[Dict], image_path: str) -> List[Dict]:
        """Add intensity data and diameter to Claude's results."""
        bgr = cv2.imread(image_path)
        if bgr is None:
            return results

        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        
        circles = []
        for idx, r in enumerate(results, start=1):
            x, y, radius = r.get("x", 0), r.get("y", 0), r.get("r", 5)
            
            diameter_nm = round((radius * 2.0) * self.nm_per_pixel, 2) if self.nm_per_pixel else None
            
            circles.append({
                "number": idx,
                "x": round(float(x), 2),
                "y": round(float(y), 2),
                "r": round(float(radius), 2),
                "diameter_nm": diameter_nm,
                "viability": r.get("viability", "needs_review"),
                "intensity": compute_radial_intensity(gray, x, y, radius),
            })
        
        return circles


async def analyze_image_ai_async(image_path: str, nm_per_pixel: float = 0.5, examples: List[Dict] = None) -> List[Dict]:
    """Async AI analysis entry point."""
    analyzer = ClaudeAIAnalyzer(nm_per_pixel=nm_per_pixel)
    results = await analyzer.analyze_with_claude_api(image_path, examples)
    return analyzer.enrich_results(results, image_path)


def analyze_image_ai(image_path: str, nm_per_pixel: float = 0.5, examples: List[Dict] = None) -> List[Dict]:
    """Sync AI analysis entry point."""
    analyzer = ClaudeAIAnalyzer(nm_per_pixel=nm_per_pixel)
    results = analyzer.analyze_image(image_path, examples)
    return analyzer.enrich_results(results, image_path)
