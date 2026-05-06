/* normalize backend boxes → canvas boxes */
export const normalizeBoxes = (boxes = []) =>
  (Array.isArray(boxes) ? boxes : []).map((b) => ({
    ...b,
    cx: b.cx ?? b.x,
    cy: b.cy ?? b.y,
  }));

// ✅ local id generator (frontend only)
export const makeId = () => `${Date.now()}_${Math.random().toString(16).slice(2)}`;

// ✅ keep stable ids by matching number (because backend doesn't return id)
export const mergeIdsByNumber = (oldBoxes, newBoxes) => {
  const safeOld = Array.isArray(oldBoxes) ? oldBoxes : [];
  const safeNew = Array.isArray(newBoxes) ? newBoxes : [];

  const map = new Map(
    safeOld
      .filter((b) => b?.number != null)
      .map((b) => [Number(b.number), b.id])
  );

  return safeNew.map((b) => ({
    ...b,
    id: map.get(Number(b.number)) || makeId(),
    cx: b.cx ?? b.x,
    cy: b.cy ?? b.y,
  }));
};

// ✅ always treat circle as array
export const toArrayBoxes = (boxes) => {
  if (Array.isArray(boxes)) return boxes;
  if (boxes && Array.isArray(boxes.boxes)) return boxes.boxes;
  return [];
};

// clamp number between min and max
export function clamp(n, a, b) {
  return Math.max(a, Math.min(b, n));
}

// normalize rect in world coords
export function normRect(r) {
  if (!r) return null;
  const x1 = Math.min(r.x1, r.x2);
  const y1 = Math.min(r.y1, r.y2);
  const x2 = Math.max(r.x1, r.x2);
  const y2 = Math.max(r.y1, r.y2);
  return { x1, y1, x2, y2, w: x2 - x1, h: y2 - y1 };
}

// circle intersects rect (fast AABB using circle bbox)
export function circleIntersectsRect(cx, cy, cr, R) {
  const cminX = cx - cr,
    cmaxX = cx + cr;
  const cminY = cy - cr,
    cmaxY = cy + cr;
  return !(cmaxX < R.x1 || cminX > R.x2 || cmaxY < R.y1 || cminY > R.y2);
}

// This function extracts a clean display name from the image file URL.
export function getImageName(url) {
  if (!url) return "";
  const fileName = url.split("/").pop();
  const namePart = fileName.split("_").slice(1).join("_");
  return namePart.replace(/\.[^/.]+$/, "");
}