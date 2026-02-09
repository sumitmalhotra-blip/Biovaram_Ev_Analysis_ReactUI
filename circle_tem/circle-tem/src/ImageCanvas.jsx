import { useEffect, useRef, useState } from "react";

/* 🔧 Normalize backend boxes → canvas boxes */
const normalizeBoxes = (boxes = []) =>
  boxes.map(b => ({
    ...b,
    cx: b.cx ?? b.x,
    cy: b.cy ?? b.y,
  }));

function ImageCanvas({ imageId, imageUrl, boxes, setBoxes, onCreateBox, onSelectBox }) {
  const canvasRef = useRef(null);
  const movedRef = useRef(false);
const [saving, setSaving] = useState(false);

  const [mode, setMode] = useState(null);
  const [active, setActive] = useState(null);

  const userId = localStorage.getItem("loginUserId");
  const API = "http://localhost:8000";
  const RESIZE_MARGIN = 8;

  /* ✅ AUTO NORMALIZE WHEN BOXES COME FROM API */
  useEffect(() => {
    if (!boxes || boxes.length === 0) return;

    const normalized = normalizeBoxes(boxes);

    const changed = normalized.some(
      (b, i) => b.cx !== boxes[i]?.cx || b.cy !== boxes[i]?.cy
    );

    if (changed) {
      setBoxes(normalized);
    }
  }, [boxes, setBoxes]);

  const hitCircle = (b, x, y) => {
    const d = Math.hypot(x - b.cx, y - b.cy);
    return d < b.r - RESIZE_MARGIN;
  };

  const hitResize = (b, x, y) => {
    const d = Math.hypot(x - b.cx, y - b.cy);
    return Math.abs(d - b.r) <= RESIZE_MARGIN;
  };

  /* 🎨 DRAW IMAGE + CIRCLES */
  useEffect(() => {
    if (!imageUrl || !boxes) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    const img = new Image();
    img.src = imageUrl;

    img.onload = () => {
      canvas.width = img.width;
      canvas.height = img.height;

      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(img, 0, 0);

      boxes.forEach(b => {
        ctx.strokeStyle =
          b.viability === "viable"
            ? "green"
            : b.viability === "non_viable"
            ? "red"
            : "orange";

        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(b.cx, b.cy, b.r, 0, Math.PI * 2);
        ctx.stroke();
      });
    };
  }, [imageUrl, JSON.stringify(boxes)]);

  const getPos = (e) => {
    const rect = canvasRef.current.getBoundingClientRect();
    const sx = canvasRef.current.width / rect.width;
    const sy = canvasRef.current.height / rect.height;
    return {
      x: (e.clientX - rect.left) * sx,
      y: (e.clientY - rect.top) * sy,
    };
  };

  const handleMouseDown = (e) => {
    movedRef.current = false;
    const { x, y } = getPos(e);

    for (let i = 0; i < boxes.length; i++) {
      if (hitResize(boxes[i], x, y)) {
        setMode("resize");
        setActive(i);
        return;
      }
      if (hitCircle(boxes[i], x, y)) {
        setMode("drag");
        setActive(i);
        return;
      }
    }
  };

  const handleMouseMove = (e) => {
    const { x, y } = getPos(e);

    if (active !== null) movedRef.current = true;

    if (active === null) {
      for (const b of boxes) {
        if (hitResize(b, x, y)) {
          canvasRef.current.style.cursor = "nwse-resize";
          return;
        }
        if (hitCircle(b, x, y)) {
          canvasRef.current.style.cursor = "move";
          return;
        }
      }
      canvasRef.current.style.cursor = "crosshair";
      return;
    }

    const updated = [...boxes];
    const b = updated[active];

    if (mode === "drag") {
      b.cx = x;
      b.cy = y;
    }

    if (mode === "resize") {
      b.r = Math.max(5, Math.hypot(x - b.cx, y - b.cy));
      b.diameter_nm = Math.round(b.r * 2);
    }

    setBoxes(updated);
  };

 const handleMouseUp = async () => {
  if (!userId || !imageId) return;

  // ✅ sanitize + normalize payload
  const payload = boxes
    .filter(b => (b.x !== undefined && b.y !== undefined) || (b.cx !== undefined && b.cy !== undefined))
    .map(b => ({
      x: b.x ?? b.cx,
      y: b.y ?? b.cy,
      r: b.r,
      diameter_nm: b.diameter_nm ?? Math.round(b.r * 2),
      viability: b.viability ?? "review",
    }));

  // 🔴 nothing valid to save
  if (payload.length === 0) {
    console.warn("No valid circles to save");
    return;
  }

  try {
    setSaving(true); // ⏳ loading start

    const res = await fetch(
      `${API}/images/${userId}/${imageId}/circles`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      }
    );

    if (!res.ok) {
      const text = await res.text();
      console.error("Save failed:", res.status, text);
    }
  } catch (err) {
    console.error("Network error:", err);
  } finally {
    setSaving(false); // ✅ loading end
  }

  setMode(null);
  setActive(null);
};

  const handleClick = (e) => {
    if (movedRef.current) return;

    const { x, y } = getPos(e);
    const idx = boxes.findIndex(b => hitCircle(b, x, y));

    if (idx !== -1) {
      onSelectBox(boxes[idx]);
    }
  };

  const handleContextMenu = (e) => {
    e.preventDefault();
    const { x, y } = getPos(e);
    onCreateBox(x, y);
  };

  return (
    <canvas
      ref={canvasRef}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onClick={handleClick}
      onContextMenu={handleContextMenu}
      style={{ maxWidth: "100%", cursor: "crosshair" }}
    />
    
  );
}

export default ImageCanvas;
