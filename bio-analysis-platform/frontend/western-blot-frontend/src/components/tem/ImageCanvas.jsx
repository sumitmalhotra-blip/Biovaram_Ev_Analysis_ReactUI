import { useEffect, useMemo, useRef, useState } from "react";
import "./ImageCanvas.css";

import IntensityPanel from "./ImageCanvasParts/IntensityPanel";
import ParticleTableView from "./ImageCanvasParts/ParticleTableView";
import RightSidebar from "./ImageCanvasParts/RightSidebar";
import { LoadingOverlay, FilterModal, ScaleModal, HelpModal } from "./ImageCanvasParts/Modals";

import {
  normalizeBoxes,
  makeId,
  mergeIdsByNumber,
  toArrayBoxes,
  clamp,
  normRect,
  circleIntersectsRect,
  getImageName,
} from "./ImageCanvasParts/canvasUtils";
import { TEM_API, STATIC_BASE } from "../../services/api";

function ImageCanvas({
  imageId,
  imageUrl,
  boxes,
  setBoxes,
  onCreateBox,
  onSelectBox,
  tableRefreshTick,
  scale: savedScale,
  setScale: setSavedScale,

  // ✅ NEW OPTIONAL PROPS (non-breaking)
  sourceFile = null,
  onShapeApiResult = null,
  setExternalImageUrl = null,
}) {
  const canvasRef = useRef(null);
  const movedRef = useRef(false);

  // ✅ SAFE boxes (never crash)
  const safeBoxes = toArrayBoxes(boxes);

  const [isRightBarOpen, setIsRightBarOpen] = useState(true);
  const [showHelp, setShowHelp] = useState(false);

  const [selectedIds, setSelectedIds] = useState(new Set());
  const [mode, setMode] = useState(null); // drag | resize | scale | intensity | select | null
  const [active, setActive] = useState(null);

  const [hoveredBox, setHoveredBox] = useState(null);
  const [hoverPos, setHoverPos] = useState({ x: 0, y: 0 });

  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(false);
  const saveAbortRef = useRef(null);

  const [selectedMethod, setSelectedMethod] = useState("rulebased");

  // ✅ table view + pagination
  const [showTable, setShowTable] = useState(false);
  const [tableLoading, setTableLoading] = useState(false);
  const [tableError, setTableError] = useState(null);

  const [sizeFilter, setSizeFilter] = useState(null);

  const [intactData, setIntactData] = useState([]);
  const [notIntactData, setNotIntactData] = useState([]);
  const [needsReviewData, setNeedsReviewData] = useState([]);

  const [showIntact, setShowIntact] = useState(false);
  const [showNotIntact, setShowNotIntact] = useState(false);

  const [pageReview, setPageReview] = useState(1);
  const [pageIntact, setPageIntact] = useState(1);
  const [pageNotIntact, setPageNotIntact] = useState(1);

  // ✅ intensity line tool
  const [isDrawingIntensity, setIsDrawingIntensity] = useState(false);
  const [intensityLine, setIntensityLine] = useState(null); // {x1,y1,x2,y2}
  const [intensityResult, setIntensityResult] = useState(null);
  const [hoverIntensityPoint, setHoverIntensityPoint] = useState(null);

  // ✅ Drag-box selection (WORLD coords)
  const [selectRect, setSelectRect] = useState(null);
  const [showGrid, setShowGrid] = useState(false);

  // ✅ scale state per image
  const [scale, setScaleState] = useState(() => {
    if (savedScale?.scale_pixels) {
      return {
        px: Number(savedScale.scale_pixels),
        value: Number(savedScale.scale_real_value),
        unit: savedScale.scale_real_unit || "nm",
      };
    }
    return { px: 0, value: 0, unit: "nm" };
  });

  // ✅ draw-scale line state
  const [scaleLine, setScaleLine] = useState(null); // {x1,y1,x2,y2,px}
  const [isDrawingScale, setIsDrawingScale] = useState(false);

  const [toast, setToast] = useState(null);

  /** Decoded display URL: data URL for TIFF images, direct URL otherwise */
  const [displayImageUrl, setDisplayImageUrl] = useState(null);

  const userId =  3;
  const API = TEM_API;
  const SHAPE_API = TEM_API;
  const RESIZE_MARGIN = 8;

  /** Strips the static base URL prefix and normalises shape-output paths to /uploads/tem/. */
  const normalizeApiImagePath = (url) => {
    const value = String(url || "").trim();
    if (!value) return "";

    // if full URL came from backend or parent
    if (value.startsWith("http://") || value.startsWith("https://")) {
      try {
        const u = new URL(value);
        return `${u.pathname}${u.search}${u.hash}`;
      } catch {
        return value.replace(STATIC_BASE, "");
      }
    }

    // if backend accidentally returns filename only
    if (!value.startsWith("/")) {
      if (
        value.includes("_shape_") ||
        value.includes("shape_classified") ||
        value.includes("shape_feedback")
      ) {
        return `/uploads/tem/${value}`;
      }
      return `/${value}`;
    }

    // repair old broken shape path: /uploads/file.jpg -> /uploads/tem/file.jpg
    if (
      value.startsWith("/uploads/") &&
      !value.startsWith("/uploads/tem/") &&
      (value.includes("_shape_") ||
        value.includes("shape_classified") ||
        value.includes("shape_feedback"))
    ) {
      const fileName = value.split("/").pop();
      return `/uploads/tem/${fileName}`;
    }

    return value;
  };

  /** Returns a fully qualified URL by prepending STATIC_BASE when necessary. */
  const toAbsoluteImageUrl = (url) => {
    const clean = normalizeApiImagePath(url);
    if (!clean) return "";
    if (clean.startsWith("http://") || clean.startsWith("https://")) return clean;
    return `${STATIC_BASE}${clean}`;
  };

  /**
   * Decodes a TIFF image from URL into a PNG data URL using the UTIF library.
   * Browsers cannot natively render TIFF in <img> or canvas — this converts to PNG first.
   * Falls back to the original URL on any error.
   */
  const decodeTiffForCanvas = async (absUrl) => {
    try {
      const UTIF = (await import("utif")).default;
      const res = await fetch(absUrl);
      if (!res.ok) throw new Error(`Failed to fetch image: ${res.status}`);
      const arrayBuffer = await res.arrayBuffer();
      const ifds = UTIF.decode(arrayBuffer);
      if (!ifds || !ifds.length) throw new Error("No TIFF frames found");
      UTIF.decodeImage(arrayBuffer, ifds[0]);
      const rgba = UTIF.toRGBA8(ifds[0]);
      const width = ifds[0].width;
      const height = ifds[0].height;
      const canvas = document.createElement("canvas");
      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext("2d");
      if (!ctx) throw new Error("Canvas 2D context unavailable");
      const imageData = ctx.createImageData(width, height);
      imageData.data.set(rgba);
      ctx.putImageData(imageData, 0, 0);
      return canvas.toDataURL("image/png");
    } catch (err) {
      console.error("[TEM] TIFF decode failed:", err);
      return absUrl;
    }
  };

  /** Resolves imageUrl to a browser-renderable URL, decoding TIFF when needed */
  useEffect(() => {
    if (!imageUrl) {
      setDisplayImageUrl(null);
      return;
    }
    const absUrl = toAbsoluteImageUrl(imageUrl);
    const lower = (imageUrl || "").toLowerCase().split("?")[0];
    if (lower.endsWith(".tif") || lower.endsWith(".tiff")) {
      decodeTiffForCanvas(absUrl).then(setDisplayImageUrl);
    } else {
      setDisplayImageUrl(absUrl);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [imageUrl]);

  // =========================================================
  // ✅ SHAPE API HELPERS (NEW - NON BREAKING)
  // =========================================================
  const mapShapeParticlesToBoxes = (particles = []) => {
    return (particles || []).map((p, index) => {
      const bbox = p?.bbox || {};
      const fx = p?.features || {};

      const x = Number(bbox.x || 0);
      const y = Number(bbox.y || 0);
      const w = Number(bbox.w || 0);
      const h = Number(bbox.h || 0);

      const cx = x + w / 2;
      const cy = y + h / 2;
      const r = Math.max(w, h) / 2;

      let viability = "needs_review";
      if (p?.color_name === "green") viability = "intact";
      else if (p?.color_name === "red") viability = "not_intact";

      return {
        id: makeId(),
        number: Number.isFinite(Number(p?.idx)) ? Number(p.idx) + 1 : index + 1,
        x: cx,
        y: cy,
        cx,
        cy,
        r,
        viability,
        diameter_nm: null,
        intensity: null,
        confidence: null,
        votes: null,
        vote_summary: null,
        membrane_intact: viability === "intact" ? true : viability === "not_intact" ? false : null,
        shape: {
          circularity: fx?.circularity ?? p?.circularity ?? null,
          solidity: fx?.solidity ?? p?.solidity ?? null,
          convexity: fx?.convexity ?? p?.convexity ?? null,
          area: fx?.area ?? p?.area ?? null,
          perimeter: fx?.perimeter ?? p?.perimeter ?? null,
          depth: fx?.depth ?? p?.depth ?? null,
        },
        bbox: { x, y, w, h },
      };
    });
  };

  const normalizeBoxesForCanvas = (boxes = []) => {
    return (Array.isArray(boxes) ? boxes : []).map((b, index) => ({
      id: b?.id || makeId(),
      number: Number.isFinite(Number(b?.number)) ? Number(b.number) : index + 1,
      ...b,
      x: Number(b?.x ?? b?.cx ?? 0),
      y: Number(b?.y ?? b?.cy ?? 0),
      cx: Number(b?.cx ?? b?.x ?? 0),
      cy: Number(b?.cy ?? b?.y ?? 0),
      r: Number(b?.r ?? 0),
    }));
  };

  const applyShapeApiResult = (data) => {
    if (!data) return [];

    const newBoxes =
      Array.isArray(data?.boxes) && data.boxes.length > 0
        ? normalizeBoxesForCanvas(data.boxes)
        : normalizeBoxesForCanvas(mapShapeParticlesToBoxes(data?.particles || []));

    setBoxes(newBoxes);

    if (typeof setExternalImageUrl === "function" && data?.result_image_url) {
      setExternalImageUrl(normalizeApiImagePath(data.result_image_url));
    }

    if (typeof onShapeApiResult === "function") {
      onShapeApiResult({
        ...data,
        result_image_url: normalizeApiImagePath(data?.result_image_url),
        clean_mask_url: normalizeApiImagePath(data?.clean_mask_url),
      });
    }

    setSelectedIds(new Set());
    setShowTable(false);
    setIntensityLine(null);
    setIntensityResult(null);
    setHoverIntensityPoint(null);

    showToastFn(
      `Shape classify done: ${data?.counts?.total ?? newBoxes.length} particles`
    );

    return newBoxes;
  };

  const handleShapeClassify = async ({
    file = sourceFile,
    clientInstructions = "",
    useAiRules = false,
    minArea = 300,
    closeKernel = 5,
    closeIterations = 2,
  } = {}) => {
    try {
      setLoading(true);

      let res;

      if (imageId) {
        const url =
          `${SHAPE_API}/images/${userId}/${imageId}/shape-classify` +
          `?client_instructions=${encodeURIComponent(clientInstructions)}` +
          `&use_ai_rules=${encodeURIComponent(useAiRules)}` +
          `&min_area=${encodeURIComponent(minArea)}` +
          `&close_kernel=${encodeURIComponent(closeKernel)}` +
          `&close_iterations=${encodeURIComponent(closeIterations)}`;

        res = await fetch(url, {
          method: "POST",
        });
      } else if (file) {
        const formData = new FormData();
        formData.append("file", file);
        formData.append("client_instructions", clientInstructions);
        formData.append("use_ai_rules", String(useAiRules));
        formData.append("min_area", String(minArea));
        formData.append("close_kernel", String(closeKernel));
        formData.append("close_iterations", String(closeIterations));

        res = await fetch(`${SHAPE_API}/shape-classify`, {
          method: "POST",
          body: formData,
        });
      } else {
        showToastFn("No source image available for shape classify");
        return;
      }

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data?.detail || "Shape classify failed");
      }

      const newBoxes = applyShapeApiResult(data);
      const targetImageId = data?.image_id || data?.imageId || imageId;

      if (targetImageId && Array.isArray(newBoxes) && newBoxes.length > 0) {
        await saveCirclesFast(newBoxes, targetImageId);
      }

      if (showTable) {
        await fetchTable();
      }
    } catch (err) {
      console.error(err);
      showToastFn(err?.message || "Shape classify failed");
    } finally {
      setLoading(false);
    }
  };

  const handleShapeClassifyWithFeedback = async ({
    file = sourceFile,
    feedbacks = [],
    clientInstructions = "",
    useAiRules = false,
    minArea = 300,
    closeKernel = 5,
    closeIterations = 2,
  } = {}) => {
    try {
      setLoading(true);

      const payload = {
        client_instructions: clientInstructions,
        use_ai_rules: useAiRules,
        min_area: minArea,
        close_kernel: closeKernel,
        close_iterations: closeIterations,
        feedbacks,
      };

      let res;

      if (file) {
        const formData = new FormData();
        formData.append("file", file);
        formData.append("payload", JSON.stringify(payload));

        res = await fetch(`${SHAPE_API}/shape-classify-with-feedback`, {
          method: "POST",
          body: formData,
        });
      } else if (imageId) {
        res = await fetch(
          `${SHAPE_API}/images/${userId}/${imageId}/shape-classify-with-feedback`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify(payload),
          }
        );
      } else {
        showToastFn("No source image available for feedback classify");
        return;
      }

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data?.detail || "Shape feedback classify failed");
      }

      applyShapeApiResult(data);
    } catch (err) {
      console.error(err);
      showToastFn(err?.message || "Shape feedback classify failed");
    } finally {
      setLoading(false);
    }
  };

  const applySelectedParticlesAsShapeFeedback = async (action, label = "") => {
    if (!selectedIds.size) {
      showToastFn("Select at least one particle");
      return;
    }

    const selectedBoxes = safeBoxes.filter((b) => selectedIds.has(b.id));

    const feedbacks = selectedBoxes.map((b, index) => ({
      matched_idx:
        Number.isFinite(Number(b?.number)) ? Number(b.number) - 1 : index,
      action,
      label,
    }));

    await handleShapeClassifyWithFeedback({
      feedbacks,
      clientInstructions: "",
      useAiRules: false,
      minArea: 300,
      closeKernel: 5,
      closeIterations: 2,
    });
  };

  const [viabilityMap] = useState({
    intact: { label: "Intact", color: "#2e7d32", bg: "#e8f5e9" },
    not_intact: { label: "Non Intact", color: "#c62828", bg: "#ffebee" },
    needs_review: { label: "Needs Review", color: "#ef6c00", bg: "#fff3e0" },
    viable: { label: "Intact", color: "#2e7d32", bg: "#e8f5e9" },
    non_viable: { label: "Non Intact", color: "#c62828", bg: "#ffebee" },
    review: { label: "Needs Review", color: "#ef6c00", bg: "#fff3e0" },
  });

  useEffect(() => {
    const preventBrowserZoom = (e) => {
      if (e.ctrlKey && e.type === "wheel") e.preventDefault();
      if (
        e.ctrlKey &&
        (e.key === "+" || e.key === "-" || e.key === "=" || e.key === "_")
      ) {
        e.preventDefault();
      }
    };

    window.addEventListener("wheel", preventBrowserZoom, { passive: false });
    window.addEventListener("keydown", preventBrowserZoom);

    return () => {
      window.removeEventListener("wheel", preventBrowserZoom);
      window.removeEventListener("keydown", preventBrowserZoom);
    };
  }, []);

  /** Displays a brief toast notification that auto-dismisses after `duration` ms. */
  const showToastFn = (message, duration = 2000) => {
    setToast(message);
    setTimeout(() => setToast(null), duration);
  };

  const [viewScale, setViewScale] = useState(1);
  const [viewOffset, setViewOffset] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const panStartRef = useRef({ sx: 0, sy: 0, ox: 0, oy: 0 });
  const spaceDownRef = useRef(false);

  const ZOOM_MIN = 1;
  const ZOOM_MAX = 9;

  useEffect(() => {
    const onKeyDown = (e) => {
      if (e.code === "Space") spaceDownRef.current = true;
    };
    const onKeyUp = (e) => {
      if (e.code === "Space") {
        spaceDownRef.current = false;
        setIsPanning(false);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("keyup", onKeyUp);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("keyup", onKeyUp);
    };
  }, []);

  const resetView = () => {
    setViewScale(1);
    setViewOffset({ x: 0, y: 0 });
  };

  const zoomAt = (factor, clientX, clientY) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const cssToCanvasX = canvas.width / rect.width;
    const cssToCanvasY = canvas.height / rect.height;

    const px = (clientX - rect.left) * cssToCanvasX;
    const py = (clientY - rect.top) * cssToCanvasY;

    const worldX = (px - viewOffset.x) / viewScale;
    const worldY = (py - viewOffset.y) / viewScale;

    const nextScale = clamp(viewScale * factor, ZOOM_MIN, ZOOM_MAX);

    const nextOffsetX = px - worldX * nextScale;
    const nextOffsetY = py - worldY * nextScale;

    setViewScale(nextScale);
    setViewOffset({ x: nextOffsetX, y: nextOffsetY });
  };

  const handleWheel = (e) => {
    if (!(e.ctrlKey || e.metaKey)) return;
    e.preventDefault();
    const direction = e.deltaY > 0 ? -1 : 1;
    const factor = direction > 0 ? 1.1 : 0.9;
    zoomAt(factor, e.clientX, e.clientY);
  };

  const [showFilterPopup, setShowFilterPopup] = useState(false);
  const [showScalePopup, setShowScalePopup] = useState(false);
  const [minNm, setMinNm] = useState(30);
  const [minNmInput, setMinNmInput] = useState(30);

  /** Returns true if particle b should be hidden because its diameter is below the minNm threshold. */
  const isHidden = (b) => {
    const threshold = Number(minNm);
    if (!Number.isFinite(threshold) || threshold <= 0) return false;

    const d = b?.diameter_nm;
    if (d == null || d === "" || !Number.isFinite(Number(d))) return false;
    return Number(d) < threshold;
  };

  /** Returns nm-per-pixel ratio for the current scale, or null when no scale is set. */
  const nmPerPixel = () => {
    if (!scale?.px || !scale?.value) return null;
    const unit = String(scale.unit || "").toLowerCase();
    if (unit === "um" || unit === "µm") return (scale.value * 1000) / scale.px;
    if (unit === "nm") return scale.value / scale.px;
    return null;
  };

  /** Returns the minimum allowed circle radius in pixels derived from minNm, or null when scale is unavailable. */
  const minRadiusPx = () => {
    const npp = nmPerPixel();
    if (!npp) return null;
    return Number(minNm || 0) / 2 / npp;
  };

  /** Loads the saved minNm threshold from the backend for the current image. */
  const fetchMinNm = async () => {
    if (!userId || !imageId) return;
    try {
      const res = await fetch(`${API}/images/${userId}/${imageId}`);
      const data = await res.json();
      setSelectedMethod(data.analysis_method);
      const v = Number(data?.min_nm);
      const finalV = Number.isFinite(v) && v > 0 ? v : 30;
      setMinNm(finalV);
      setMinNmInput(finalV);
    } catch {
      setMinNm(30);
      setMinNmInput(30);
    }
  };

  /** Persists the 'Hide particles below' threshold to the backend. Enforces a minimum of 30 nm. */
  const saveMinNm = async () => {
    if (!userId || !imageId) return;

    const v = Number(minNmInput);
    if (!Number.isFinite(v) || v <= 0) {
      showToastFn("Please enter a valid nm number (e.g. 30, 40, 50)");
      return;
    }
    if (v < 30) {
      showToastFn("Minimum allowed value is 30 nm");
      setMinNmInput(30);
      return;
    }

    try {
      const res = await fetch(`${API}/images/${userId}/${imageId}/min_nm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ min_nm: v }),
      });

      const data = await res.json();
      const vv = Number(data?.min_nm);
      const finalV = Number.isFinite(vv) && vv > 0 ? vv : v;

      setMinNm(finalV);
      setMinNmInput(finalV);
      setShowFilterPopup(false);

      setSelectedIds(new Set());

      if (Array.isArray(data?.boxes)) {
        setBoxes(mergeIdsByNumber(safeBoxes, data.boxes));
      }

      if (showTable) fetchTable();
      showToastFn(`Hidden below ${finalV} nm`);
    } catch (e) {
      console.error(e);
      alert("Failed to save filter");
    }
  };

  useEffect(() => {
    if (!safeBoxes.length) return;
    setSelectedIds((prev) => {
      const next = new Set();
      safeBoxes.forEach((b) => {
        if (prev.has(b.id) && !isHidden(b)) next.add(b.id);
      });
      return next;
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [minNm, imageId]);

  /** Computes diameter in nm for particle b using the current scale. Returns null when scale is not set. */
  const diameterNmFor = (b) => {
    const npp = nmPerPixel();
    if (!npp) return null;
    return Math.round(Number(b.r ?? 20) * 2 * npp);
  };

  const radiusPxFor = (b) => {
    const npp = nmPerPixel();
    const d = b?.diameter_nm;
    if (d != null && d !== "" && Number(d) > 0 && npp) {
      return Number(d) / npp / 2;
    }
    return Number(b.r ?? 20);
  };

  const hitCircle = (b, x, y) => {
    if (isHidden(b)) return false;
    const r = radiusPxFor(b);
    const cx = b.cx ?? b.x;
    const cy = b.cy ?? b.y;
    return Math.hypot(x - cx, y - cy) < r - RESIZE_MARGIN;
  };

  const hitResize = (b, x, y) => {
    if (isHidden(b)) return false;
    const r = radiusPxFor(b);
    const cx = b.cx ?? b.x;
    const cy = b.cy ?? b.y;
    return Math.abs(Math.hypot(x - cx, y - cy) - r) <= RESIZE_MARGIN;
  };

  const fetchTable = async (overrideSize = undefined) => {
    if (!imageId) return;

    const effectiveSize = overrideSize !== undefined ? overrideSize : sizeFilter;
    const query = effectiveSize ? `?size=${encodeURIComponent(effectiveSize)}` : "";

    try {
      setTableLoading(true);
      setTableError(null);

      const [intactRes, notIntactRes, reviewRes] = await Promise.all([
        fetch(`${API}/images/${imageId}/table/intact${query}`),
        fetch(`${API}/images/${imageId}/table/not_intact${query}`),
        fetch(`${API}/images/${imageId}/table/needs_review${query}`),
      ]);

      if (!intactRes.ok || !notIntactRes.ok || !reviewRes.ok) {
        setTableError("Failed to load table data (server error)");
        return;
      }

      setIsRightBarOpen(false);
      const intactJson = await intactRes.json();
      const notIntactJson = await notIntactRes.json();
      const reviewJson = await reviewRes.json();

      if (intactJson.error || notIntactJson.error || reviewJson.error) {
        setTableError("Failed to load table data");
        return;
      }

      setIntactData(intactJson.circles || []);
      setNotIntactData(notIntactJson.circles || []);
      setNeedsReviewData(reviewJson.circles || []);

      setPageReview(1);
      setPageIntact(1);
      setPageNotIntact(1);
      setShowIntact(false);
      setShowNotIntact(false);
    } catch (e) {
      console.error(e);
      setTableError("Failed to load table");
    } finally {
      setTableLoading(false);
    }
  };

  const toggleSelect = (id) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const clearSelection = () => setSelectedIds(new Set());

  /**
   * Saves the current circle set to the backend with debounce via AbortController.
   * Any in-flight previous save is cancelled before sending the new payload.
   */
  const saveCirclesFast = async (boxesToSave, targetImageId = imageId) => {
    if (!userId || !targetImageId) {
      console.warn("saveCirclesFast skipped", { userId, targetImageId });
      return;
    }

    if (saveAbortRef.current) {
      try {
        saveAbortRef.current.abort();
      } catch {}
    }

    const controller = new AbortController();
    saveAbortRef.current = controller;

    const npp = nmPerPixel();

    const payload = (Array.isArray(boxesToSave) ? boxesToSave : []).map((b) => {
      let rSend = Number(b.r ?? 20);

      if (
        b.diameter_nm != null &&
        b.diameter_nm !== "" &&
        Number(b.diameter_nm) > 0 &&
        npp
      ) {
        rSend = Number(b.diameter_nm) / npp / 2;
      }

      return {
        number: b.number ?? null,
        x: Number(b.x ?? b.cx),
        y: Number(b.y ?? b.cy),
        r: Number(rSend),
        diameter_nm: b.diameter_nm ?? null,
        viability: b.viability ?? "needs_review",
        intensity: b.intensity ?? null,
        shape: b.shape ?? null,
      };
    });

    let res;
    try {
      res = await fetch(`${API}/images/${userId}/${targetImageId}/circles?fast=1`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });
    } catch (fetchErr) {
      if (fetchErr?.name === "AbortError") throw fetchErr;
      throw new Error("Network error: could not reach backend");
    }

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data?.detail || `Save failed (HTTP ${res.status})`);
    }

    if (Array.isArray(data?.boxes)) {
      setBoxes(mergeIdsByNumber(boxesToSave, data.boxes));
    }

    return data;
  };

  const bulkUpdateViability = async (newValue) => {
    if (!selectedIds.size) return;
    setLoading(true);

    const updated = safeBoxes.map((b) =>
      selectedIds.has(b.id) ? { ...b, viability: newValue } : b
    );
    setBoxes(updated);

    try {
      await saveCirclesFast(updated);
      if (showTable) fetchTable();
      clearSelection();
    } catch (e) {
      if (e?.name !== "AbortError") {
        console.error(e);
        showToastFn("Failed to update particles. Changes may not be saved.");
      }
    } finally {
      setLoading(false);
    }
  };

  const scrollToBoxOnCanvas = (box) => {
    const canvas = canvasRef.current;
    if (!canvas || !box) return;

    const scroller = canvas.closest('[data-scroll="rightpanel"]');
    if (!scroller) return;

    const scrollerRect = scroller.getBoundingClientRect();
    const canvasRect = canvas.getBoundingClientRect();
    const cssScaleY = canvasRect.height / canvas.height;

    const yOnCanvasPx = box.cy * viewScale + viewOffset.y;
    const boxYOnScreen = canvasRect.top - scrollerRect.top + yOnCanvasPx * cssScaleY;

    const targetTop = scroller.scrollTop + boxYOnScreen - scroller.clientHeight / 2;
    scroller.scrollTo({ top: Math.max(0, targetTop), behavior: "smooth" });
  };

  const focusParticleByNumber = (num) => {
    const n = Number(num);
    if (!Number.isFinite(n)) return;

    const found = safeBoxes.find((b) => Number(b.number) === n);
    if (!found) {
      showToastFn(`Particle ${n} not found on image`);
      return;
    }

    if (isHidden(found)) {
      showToastFn(`Particle ${n} is hidden (< ${minNm} nm)`);
      return;
    }

    setShowTable(false);
    setSelectedIds(new Set([found.id]));

    requestAnimationFrame(() => {
      requestAnimationFrame(() => scrollToBoxOnCanvas(found));
    });

    showToastFn(`Focused particle ${n}`);
  };

  useEffect(() => {
    if (showTable) fetchTable();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tableRefreshTick]);

  useEffect(() => {
    if (!imageUrl) return;

    const normalized = normalizeBoxes(safeBoxes).map((b) => ({
      ...b,
      id: b.id || makeId(),
    }));
    setBoxes(normalized);

    if (savedScale?.scale_pixels) {
      setScaleState({
        px: Number(savedScale.scale_pixels),
        value: Number(savedScale.scale_real_value),
        unit: savedScale.scale_real_unit || "nm",
      });
    } else {
      setScaleState({ px: 0, value: 0, unit: "nm" });
    }

    setScaleLine(null);
    setIsDrawingScale(false);
    setMode(null);
    setActive(null);

    setShowTable(false);
    setTableError(null);
    setTableLoading(false);
    setPageReview(1);
    setPageIntact(1);
    setPageNotIntact(1);
    setSelectedIds(new Set());
    setShowIntact(false);
    setShowNotIntact(false);

    setIntensityLine(null);
    setIntensityResult(null);
    setHoverIntensityPoint(null);

    setSelectRect(null);

    resetView();
    fetchMinNm();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [imageUrl, imageId]);

  const boxesKey = useMemo(() => {
    return safeBoxes
      .map(
        (b) =>
          `${b.id}:${b.cx ?? b.x},${b.cy ?? b.y},${b.r},${b.diameter_nm},${b.viability},${b.number}`
      )
      .join("|");
  }, [safeBoxes]);

  const selectedKey = useMemo(() => Array.from(selectedIds).join("|"), [selectedIds]);

  useEffect(() => {
    if (!displayImageUrl) return;
    if (showTable) return;
    if (!canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const finalImageUrl = displayImageUrl;
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.src = finalImageUrl;

    const draw = () => {
      if (!canvasRef.current) return;

      canvas.width = img.width;
      canvas.height = img.height;

      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      ctx.setTransform(viewScale, 0, 0, viewScale, viewOffset.x, viewOffset.y);
      ctx.drawImage(img, 0, 0);

      if (showGrid) {
        const cellSize = 600;
        const cols = Math.ceil(img.width / cellSize);
        const rows = Math.ceil(img.height / cellSize);

        ctx.save();
        ctx.strokeStyle = "rgba(0,255,255,0.55)";
        ctx.lineWidth = 2.5 / viewScale;

        for (let i = 0; i <= cols; i++) {
          const gx = i * cellSize;
          ctx.beginPath();
          ctx.moveTo(gx, 0);
          ctx.lineTo(gx, img.height);
          ctx.stroke();
        }

        for (let j = 0; j <= rows; j++) {
          const gy = j * cellSize;
          ctx.beginPath();
          ctx.moveTo(0, gy);
          ctx.lineTo(img.width, gy);
          ctx.stroke();
        }

        ctx.restore();
      }

      safeBoxes.forEach((b) => {
        if (isHidden(b)) return;

        const cx = b.cx ?? b.x;
        const cy = b.cy ?? b.y;
        const rPx = radiusPxFor(b);

        ctx.strokeStyle =
          b.viability === "intact"
            ? "green"
            : b.viability === "not_intact"
            ? "red"
            : "orange";

        ctx.lineWidth = 5 / viewScale;
        ctx.beginPath();
        ctx.arc(cx, cy, rPx, 0, Math.PI * 2);
        ctx.stroke();

        if (selectedIds.has(b.id)) {
          ctx.save();
          ctx.setLineDash([]);
          ctx.lineWidth = 6 / viewScale;
          ctx.strokeStyle = "#00bcd4";
          ctx.beginPath();
          ctx.arc(cx, cy, rPx, 0, Math.PI * 2);
          ctx.stroke();

          ctx.fillStyle = "#00bcd4";
          ctx.beginPath();
          ctx.arc(cx, cy, Math.max(4 / viewScale, Math.min(10 / viewScale, (rPx * 0.15))), 0, Math.PI * 2);
          ctx.fill();
          ctx.restore();
        }

        if (b.number != null && b.number !== "") {
          const label = String(b.number);
          const fontSize = Math.max(12 / viewScale, Math.min(28 / viewScale, Math.floor(rPx * 0.5)));

          ctx.save();
          ctx.font = `bold ${fontSize}px Arial`;
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";

          const tx = Math.round(cx);
          const ty = Math.round(cy);

          ctx.lineWidth = 5 / viewScale;
          ctx.strokeStyle = "black";
          ctx.strokeText(label, tx, ty);

          ctx.fillStyle = "white";
          ctx.fillText(label, tx, ty);
          ctx.restore();
        }
      });

      if (scaleLine) {
        ctx.save();
        ctx.strokeStyle = "cyan";
        ctx.lineWidth = 6 / viewScale;
        ctx.beginPath();
        ctx.moveTo(scaleLine.x1, scaleLine.y1);
        ctx.lineTo(scaleLine.x2, scaleLine.y2);
        ctx.stroke();

        const midX = (scaleLine.x1 + scaleLine.x2) / 2;
        const midY = (scaleLine.y1 + scaleLine.y2) / 2;

        ctx.fillStyle = "cyan";
        ctx.font = `${24 / viewScale}px Arial`;
        ctx.textAlign = "center";
        ctx.textBaseline = "bottom";
        ctx.fillText(`${scaleLine.px}px`, midX, midY - 10 / viewScale);
        ctx.restore();
      }

      if (intensityLine) {
        ctx.save();

        ctx.strokeStyle = "magenta";
        ctx.lineWidth = 5 / viewScale;
        ctx.beginPath();
        ctx.moveTo(intensityLine.x1, intensityLine.y1);
        ctx.lineTo(intensityLine.x2, intensityLine.y2);
        ctx.stroke();

        if (intensityResult?.points?.length) {
          intensityResult.points.forEach((p) => {
            const x = p.x;
            const y = p.y;

            ctx.beginPath();
            ctx.arc(x, y, 6 / viewScale, 0, Math.PI * 2);
            ctx.fillStyle = "white";
            ctx.fill();

            ctx.lineWidth = 2 / viewScale;
            ctx.strokeStyle = "#00ffff";
            ctx.stroke();
          });
        }

        ctx.restore();
      }

      if (hoverIntensityPoint?.x != null && hoverIntensityPoint?.y != null) {
        const hx = hoverIntensityPoint.x;
        const hy = hoverIntensityPoint.y;

        ctx.save();
        ctx.beginPath();
        ctx.arc(hx, hy, 10 / viewScale, 0, Math.PI * 2);
        ctx.strokeStyle = "rgba(255, 28, 32, 0.95)";
        ctx.lineWidth = 3 / viewScale;
        ctx.stroke();

        ctx.beginPath();
        ctx.moveTo(hx - 18 / viewScale, hy);
        ctx.lineTo(hx + 18 / viewScale, hy);
        ctx.moveTo(hx, hy - 18 / viewScale);
        ctx.lineTo(hx, hy + 18 / viewScale);
        ctx.strokeStyle = "rgba(218, 21, 21, 0.75)";
        ctx.lineWidth = 2 / viewScale;
        ctx.stroke();
        ctx.restore();
      }

      if (selectRect && mode === "select") {
        const R = normRect(selectRect);
        if (R && R.w > 1 && R.h > 1) {
          ctx.save();
          ctx.globalAlpha = 0.18;
          ctx.fillStyle = "#00bcd4";
          ctx.fillRect(R.x1, R.y1, R.w, R.h);

          ctx.globalAlpha = 0.95;
          ctx.strokeStyle = "#00bcd4";
          ctx.lineWidth = 3 / viewScale;
          ctx.setLineDash([10 / viewScale, 6 / viewScale]);
          ctx.strokeRect(R.x1, R.y1, R.w, R.h);
          ctx.restore();
        }
      }

      ctx.setTransform(1, 0, 0, 1, 0, 0);

      if (showGrid) {
        const cellSize = 200;
        const cols = Math.ceil(img.width / cellSize);
        const rows = Math.ceil(img.height / cellSize);

        const getColumnLabel = (index) => {
          let label = "";
          let n = index;
          while (n >= 0) {
            label = String.fromCharCode((n % 26) + 65) + label;
            n = Math.floor(n / 26) - 1;
          }
          return label;
        };

        const topBarHeight = 32;
        const leftBarWidth = 40;

        ctx.save();

        ctx.fillStyle = "rgba(0, 0, 0, 0.55)";
        ctx.fillRect(0, 0, canvas.width, topBarHeight);

        ctx.fillRect(0, 0, leftBarWidth, canvas.height);

        ctx.fillStyle = "rgba(0, 0, 0, 0.75)";
        ctx.fillRect(0, 0, leftBarWidth, topBarHeight);

        ctx.strokeStyle = "rgba(0,255,255,0.55)";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(leftBarWidth, 0);
        ctx.lineTo(leftBarWidth, canvas.height);
        ctx.stroke();

        ctx.beginPath();
        ctx.moveTo(0, topBarHeight);
        ctx.lineTo(canvas.width, topBarHeight);
        ctx.stroke();

        ctx.font = "bold 40px Arial";
        ctx.fillStyle = "rgba(0,255,255,0.55)";
        ctx.strokeStyle = "black";
        ctx.lineWidth = 3;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";

        for (let i = 0; i < cols; i++) {
          const worldX = i * cellSize + cellSize / 2;
          const screenX = worldX * viewScale + viewOffset.x;

          if (screenX >= leftBarWidth && screenX <= canvas.width) {
            const label = getColumnLabel(i);
            ctx.strokeText(label, screenX, topBarHeight / 2);
            ctx.fillText(label, screenX, topBarHeight / 2);
          }
        }

        for (let j = 0; j < rows; j++) {
          const worldY = j * cellSize + cellSize / 2;
          const screenY = worldY * viewScale + viewOffset.y;

          if (screenY >= topBarHeight && screenY <= canvas.height) {
            const label = String(j + 1);
            ctx.strokeText(label, leftBarWidth / 2, screenY);
            ctx.fillText(label, leftBarWidth / 2, screenY);
          }
        }

        ctx.restore();
      }

      ctx.setTransform(1, 0, 0, 1, 0, 0);
    };

    img.onload = draw;
    img.onerror = () => {
      console.error("Failed to load image:", finalImageUrl);
      showToastFn("Failed to load image preview");
    };
    if (img.complete) draw();

    return () => {
      img.onload = null;
      img.onerror = null;
      img.src = "";
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    displayImageUrl,
    showTable,
    scaleLine,
    scale.value,
    scale.px,
    scale.unit,
    boxesKey,
    selectedKey,
    minNm,
    viewScale,
    viewOffset.x,
    viewOffset.y,
    intensityLine,
    intensityResult,
    hoverIntensityPoint,
    selectRect,
    mode,
    showGrid,
  ]);

  const getPos = (e) => {
    const rect = canvasRef.current.getBoundingClientRect();
    const sx = canvasRef.current.width / rect.width;
    const sy = canvasRef.current.height / rect.height;

    const px = (e.clientX - rect.left) * sx;
    const py = (e.clientY - rect.top) * sy;

    const x = (px - viewOffset.x) / viewScale;
    const y = (py - viewOffset.y) / viewScale;

    return { x, y, px, py };
  };

  const handleMouseDown = (e) => {
    movedRef.current = false;

    if (!showTable && spaceDownRef.current && !isDrawingScale) {
      setIsPanning(true);
      panStartRef.current = {
        sx: e.clientX,
        sy: e.clientY,
        ox: viewOffset.x,
        oy: viewOffset.y,
      };
      return;
    }

    if (!showTable && isDrawingIntensity) {
      setMode("intensity");
      const { x, y } = getPos(e);
      setIntensityLine({ x1: x, y1: y, x2: x, y2: y });
      canvasRef.current.style.cursor = "crosshair";
      return;
    }

    const { x, y } = getPos(e);

    if (isDrawingScale) {
      setMode("scale");
      setScaleLine({ x1: x, y1: y, x2: x, y2: y, px: 0 });
      return;
    }

    if (!showTable && e.button === 0 && e.shiftKey && !isPanning && !isDrawingScale) {
      let hitSomething = false;
      for (let i = 0; i < safeBoxes.length; i++) {
        if (hitResize(safeBoxes[i], x, y) || hitCircle(safeBoxes[i], x, y)) {
          hitSomething = true;
          break;
        }
      }
      if (!hitSomething) {
        setMode("select");
        setActive(null);
        setSelectRect({ x1: x, y1: y, x2: x, y2: y });
        canvasRef.current.style.cursor = "crosshair";
        return;
      }
    }

    for (let i = 0; i < safeBoxes.length; i++) {
      if (hitResize(safeBoxes[i], x, y)) {
        const minR = minRadiusPx();
        if (minR != null) {
          const rNow = radiusPxFor(safeBoxes[i]);
          if (rNow < minR) {
            showToastFn(`This circle is below ${minNm}nm. Resize not allowed.`);
            return;
          }
        }
        setMode("resize");
        setActive(i);
        return;
      }

      if (hitCircle(safeBoxes[i], x, y)) {
        setMode("drag");
        setActive(i);
        return;
      }
    }
  };

  const handleMouseMove = (e) => {
    if (mode === "select" && selectRect) {
      movedRef.current = true;
      const { x, y } = getPos(e);
      setSelectRect((prev) => (prev ? { ...prev, x2: x, y2: y } : prev));
      canvasRef.current.style.cursor = "crosshair";
      return;
    }

    if (isPanning) {
      movedRef.current = true;
      const dx = e.clientX - panStartRef.current.sx;
      const dy = e.clientY - panStartRef.current.sy;

      const canvas = canvasRef.current;
      const rect = canvas.getBoundingClientRect();
      const sx = canvas.width / rect.width;
      const sy = canvas.height / rect.height;

      setViewOffset({
        x: panStartRef.current.ox + dx * sx,
        y: panStartRef.current.oy + dy * sy,
      });
      canvasRef.current.style.cursor = "grab";
      return;
    }

    if (mode === "intensity" && intensityLine) {
      const { x, y } = getPos(e);
      setIntensityLine({ ...intensityLine, x2: x, y2: y });
      canvasRef.current.style.cursor = "crosshair";
      return;
    }

    const { x, y } = getPos(e);

    let hovered = null;
    for (const b of safeBoxes) {
      if (hitCircle(b, x, y)) {
        hovered = b;
        break;
      }
    }
    if (hovered) {
      setHoveredBox(hovered);
      setHoverPos({ x: e.clientX, y: e.clientY });
    } else {
      setHoveredBox(null);
    }

    if (mode === "scale" && scaleLine) {
      const px = Math.round(Math.hypot(x - scaleLine.x1, y - scaleLine.y1));
      setScaleLine({ ...scaleLine, x2: x, y2: y, px });
      return;
    }

    if (active !== null) {
      movedRef.current = true;

      const updated = [...safeBoxes];
      const b = updated[active];
      if (!b) return;

      if (isHidden(b)) {
        setMode(null);
        setActive(null);
        return;
      }

      if (mode === "drag") {
        b.cx = x;
        b.cy = y;
        b.x = x;
        b.y = y;
      }

      if (mode === "resize") {
        const rawR = Math.max(5, Math.hypot(x - (b.cx ?? b.x), y - (b.cy ?? b.y)));
        const minR = minRadiusPx();

        if (minR == null) {
          // No scale set — allow free resize but never below 5px
          b.r = rawR;
          const dnm = diameterNmFor(b);
          b.diameter_nm = dnm ?? b.diameter_nm ?? null;
        } else {
          // Clamp radius so diameter never falls below the 'Hide particles below' threshold
          const clampedR = Math.max(rawR, minR);
          b.r = clampedR;
          const npp = nmPerPixel();
          b.diameter_nm = npp ? Math.round(clampedR * 2 * npp) : b.diameter_nm ?? null;
        }
      }

      setBoxes(updated);
      return;
    }

    for (const b of safeBoxes) {
      if (hitResize(b, x, y)) {
        canvasRef.current.style.cursor = "nwse-resize";
        return;
      }
      if (hitCircle(b, x, y)) {
        canvasRef.current.style.cursor = "move";
        return;
      }
    }

    if (spaceDownRef.current) {
      canvasRef.current.style.cursor = "grab";
      return;
    }

    canvasRef.current.style.cursor = "crosshair";
  };

  const reanalyzeImage = async (userId, imageId, method) => {
    const res = await fetch(
      `${API}/images/${userId}/${imageId}/reanalyze?method=${encodeURIComponent(method)}`,
      { method: "POST" }
    );

    if (!res.ok) {
      const errText = await res.text();
      throw new Error(errText || "Reanalyze failed");
    }
    return res.json();
  };

  const onReanalyze = async (method) => {
    try {
      setLoading(true);
      const data = await reanalyzeImage(String(userId), imageId, method);
      if (Array.isArray(data?.boxes)) setBoxes(data.boxes);

      if (typeof setExternalImageUrl === "function" && data?.image_url) {
        setExternalImageUrl(normalizeApiImagePath(data.image_url));
      }
    } catch (e) {
      console.error(e);
      showToastFn(`Reanalyze failed: ${e?.message || "Check backend logs."}`);
    } finally {
      setLoading(false);
    }
  };

  const onShapeClassify = async () => {
    await handleShapeClassify({
      file: sourceFile,
      clientInstructions: "",
      useAiRules: false,
      minArea: 300,
      closeKernel: 5,
      closeIterations: 2,
    });
  };

  const handleMouseUp = async (e) => {
    if (!userId || !imageId) return;

    if (mode === "select" && selectRect) {
      const R = normRect(selectRect);
      setMode(null);
      setSelectRect(null);

      if (!R || R.w < 2 || R.h < 2) return;

      const picked = new Set();
      for (const b of safeBoxes) {
        if (!b || isHidden(b)) continue;
        const cx = Number(b.cx ?? b.x);
        const cy = Number(b.cy ?? b.y);
        const r = Number(radiusPxFor(b));
        if (!Number.isFinite(cx) || !Number.isFinite(cy) || !Number.isFinite(r)) continue;

        if (circleIntersectsRect(cx, cy, r, R)) {
          picked.add(b.id);
        }
      }

      const addMode = e?.ctrlKey || e?.metaKey;
      setSelectedIds((prev) => {
        if (!addMode) return picked;
        const next = new Set(prev);
        picked.forEach((id) => next.add(id));
        return next;
      });

      showToastFn(`Selected ${picked.size} particle(s)`);
      return;
    }

    if (isPanning) {
      setIsPanning(false);
      setMode(null);
      setActive(null);
      return;
    }

    if (mode === "scale") {
      setMode(null);
      setIsDrawingScale(false);

      setIsDrawingIntensity(false);
      setIntensityLine(null);

      if (scaleLine?.px > 0) {
        setScaleState((prev) => ({ ...prev, px: scaleLine.px }));
        setShowScalePopup(true);
        setShowFilterPopup(false);
        setShowTable(false);
      }
      return;
    }

    if (mode === "intensity" && intensityLine) {
      setMode(null);
      setIsDrawingIntensity(false);

      try {
        setLoading(true);

        const payload = {
          image_id: imageId,
          x1: intensityLine.x1,
          y1: intensityLine.y1,
          x2: intensityLine.x2,
          y2: intensityLine.y2,
          samples: 20,
        };

        const res = await fetch(`${API}/line-intensity`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });

        if (!res.ok) throw new Error(`Server error: ${res.status}`);
        const data = await res.json();
        setIntensityResult(data);
        setHoverIntensityPoint(null);

        showToastFn(
          data?.average_intensity != null
            ? `Line intensity avg: ${Number(data.average_intensity).toFixed(1)}`
            : "Intensity done"
        );
      } catch (e) {
        console.error(e);
        showToastFn(`Intensity failed: ${e?.message || "Unknown error"}`);
      } finally {
        setLoading(false);
      }

      return;
    }

    if (!movedRef.current) {
      setMode(null);
      setActive(null);
      return;
    }

    try {
      setSaving(true);
      await saveCirclesFast(safeBoxes);
    } catch (e2) {
      if (e2?.name !== "AbortError") {
        console.error(e2);
        showToastFn("Failed to save changes. Please try again.");
      }
    } finally {
      setSaving(false);
      setMode(null);
      setActive(null);
    }
  };

  const handleClick = (e) => {
    if (movedRef.current) return;
    if (isDrawingScale) return;
    if (isPanning) return;
    if (mode === "select") return;

    const { x, y } = getPos(e);
    const idx = safeBoxes.findIndex((b) => hitCircle(b, x, y));

    if (idx === -1) {
      clearSelection();
      return;
    }

    const clicked = safeBoxes[idx];

    if (e.ctrlKey || e.metaKey) {
      toggleSelect(clicked.id);
      return;
    }

    clearSelection();
    onSelectBox(clicked);
  };

  const handleContextMenu = (e) => {
    e.preventDefault();
    if (isDrawingScale) return;
    if (isPanning) return;
    if (mode === "select") return;

    const { x, y } = getPos(e);
    onCreateBox(x, y);

    setTimeout(() => {
      setBoxes((prev) => {
        const arr = toArrayBoxes(prev);
        if (arr.length === 0) return arr;

        const idx = arr.length - 1;
        const last = arr[idx];
        if (!last) return arr;

        const minR = minRadiusPx();
        if (minR == null) {
          showToastFn("Set scale to enforce min nm filter");
          return arr;
        }

        const currentR = Number(last.r ?? 20);
        const newR = Math.max(currentR, minR);
        if (newR === currentR) return arr;

        const npp = nmPerPixel();
        const newDiameterNm = npp ? Math.round(newR * 2 * npp) : last.diameter_nm ?? null;

        const updated = [...arr];
        updated[idx] = {
          ...last,
          r: newR,
          diameter_nm: newDiameterNm,
          cx: last.cx ?? last.x ?? x,
          cy: last.cy ?? last.y ?? y,
          x: last.x ?? last.cx ?? x,
          y: last.y ?? last.cy ?? y,
          id: last.id || makeId(),
        };
        return updated;
      });
    }, 0);
  };

  const handleTableClick = async () => {
    setShowScalePopup(false);
    setShowFilterPopup(false);

    const next = !showTable;
    setShowTable(next);

    if (next) {
      await fetchTable();
    }
  };

  const handleScaleField = (field, value) => {
    if (field === "unit") {
      setScaleState((prev) => ({ ...prev, unit: value }));
      return;
    }
    setScaleState((prev) => ({ ...prev, [field]: Number(value) }));
  };

  const recalcDiametersWithScale = () => {
    const npp = nmPerPixel();
    if (!npp) return;
    const updated = safeBoxes.map((b) => ({
      ...b,
      diameter_nm: Math.round(Number(b.r ?? 20) * 2 * npp),
    }));
    setBoxes(updated);
  };

  const saveScaleToBackend = async () => {
    if (!userId || !imageId) return;
    if (!scale?.px || !scale?.value || !scale?.unit) {
      alert("Please set scale value, unit, and draw a valid scale line (pixels).");
      return;
    }

    try {
      const payload = {
        scale_pixels: Number(scale.px),
        scale_real_value: Number(scale.value),
        scale_real_unit: scale.unit,
      };

      const res = await fetch(`${API}/images/${userId}/${imageId}/scale`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json();

      if (data?.scale) {
        setSavedScale(data.scale);
        setScaleState({
          px: Number(data.scale.scale_pixels),
          value: Number(data.scale.scale_real_value),
          unit: data.scale.scale_real_unit || "nm",
        });
        recalcDiametersWithScale();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const bulkDeleteSelected = async () => {
    if (!userId || !imageId) return;
    if (!selectedIds.size) return;

    const numbers = safeBoxes
      .filter((b) => selectedIds.has(b.id))
      .map((b) => Number(b.number))
      .filter((n) => Number.isFinite(n));

    if (!numbers.length) {
      showToastFn("No valid particle numbers to delete");
      return;
    }

    try {
      setLoading(true);

      const res = await fetch(`${API}/images/${userId}/${imageId}/circles/delete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ numbers }),
      });

      const data = await res.json();

      if (Array.isArray(data?.boxes)) {
        const normalized = normalizeBoxes(data.boxes).map((b) => ({
          ...b,
          id: makeId(),
        }));
        setBoxes(normalized);
      }

      clearSelection();
      if (showTable) fetchTable();
      showToastFn(`Deleted ${numbers.length} particle(s)`);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const [infoOpen, setInfoOpen] = useState(false);
  const [infoPos, setInfoPos] = useState({ top: 0, left: 0 });

  const descriptions = [
    "CNN: Deep learning–based particle detection with CNN",
    "Rule-Based: Fast particle detection using predefined rules",
  ];

  const openInfo = (e) => {
    const rect = e?.currentTarget?.getBoundingClientRect();
    if (!rect) return;

    setInfoPos({
      top: rect.bottom + 8,
      left: rect.left - 260,
    });

    setInfoOpen(true);
  };

  const closeInfo = () => setInfoOpen(false);
  const toggleInfo = (e) => (infoOpen ? closeInfo() : openInfo(e));

  const handleFilterClick = () => {
    setShowFilterPopup(true);
    setShowScalePopup(false);
    setShowTable(false);
  };

  const handleSettingsClick = () => {
    setShowScalePopup(true);
    setShowFilterPopup(false);
    setShowTable(false);

    setIsDrawingIntensity(false);
    setIntensityLine(null);
  };

  const startIntensityTool = () => {
    setIsDrawingIntensity(true);
    setMode(null);
    setActive(null);
    setIntensityLine(null);
    setIntensityResult(null);
    setHoverIntensityPoint(null);
    setShowFilterPopup(false);
    setShowTable(false);
    showToastFn("Intensity tool: Draw a vertical line (click → drag → release)");
  };

  return (
    <>
      <LoadingOverlay loading={loading} />

      {selectedIds.size > 0 && (
        <div className="bulkBar">
          <div className="bulkCount">Selected: {selectedIds.size}</div>

          <button
            className="bulkBtn bulkBtn--intact"
            onClick={() => bulkUpdateViability("intact")}
            disabled={loading}
          >
            Mark Intact
          </button>
          <button
            className="bulkBtn bulkBtn--notintact"
            onClick={() => bulkUpdateViability("not_intact")}
            disabled={loading}
          >
            Mark Non Intact
          </button>
          <button
            className="bulkBtn bulkBtn--review"
            onClick={() => bulkUpdateViability("needs_review")}
            disabled={loading}
          >
            Mark Needs Review
          </button>

          <button className="bulkBtn bulkBtn--clear" onClick={bulkDeleteSelected} disabled={loading}>
            Delete
          </button>

          <button className="bulkBtn bulkBtn--clear" onClick={clearSelection}>
            Clear
          </button>
        </div>
      )}

      {toast && <div className="toast">{toast}</div>}

      <IntensityPanel
        result={intensityResult}
        onClose={() => {
          setIntensityResult(null);
          setHoverIntensityPoint(null);
          setIntensityLine(null);
        }}
        onHoverPoint={setHoverIntensityPoint}
      />

      <div className="temLayout">
        <div className="stage">
          {!showTable && (
            <canvas
              ref={canvasRef}
              className="temCanvas"
              onWheel={handleWheel}
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onClick={handleClick}
              onContextMenu={handleContextMenu}
            />
          )}

          {loading && <div className="tableMsg">Loading...</div>}

          {!showTable && hoveredBox && !isHidden(hoveredBox) && (
            <div className="tooltip" style={{ top: hoverPos.y + 12, left: hoverPos.x + 12 }}>
              <div>
                {hoveredBox?.intensity && (
                  <>
                    <div>
                      <b>Center:</b> {hoveredBox.intensity.center_intensity}
                    </div>
                    <div>
                      <b>Edge:</b> {hoveredBox.intensity.edge_intensity}
                    </div>
                    <div>
                      <b>Mean:</b> {hoveredBox.intensity.mean_intensity}
                    </div>
                    <div className="tooltipGap" />
                  </>
                )}
                <b>Diameter:</b>{" "}
                {(() => {
                  const d = hoveredBox.diameter_nm ?? diameterNmFor(hoveredBox);
                  if (!d) return "Scale not set";
                  return `${d} nm`;
                })()}
              </div>
            </div>
          )}

          {!showTable && saving && <div className="saving">Saving...</div>}

          {showTable && (
            <ParticleTableView
              imageUrl={imageUrl}
              minNm={minNm}
              showTable={showTable}
              setShowTable={setShowTable}
              viabilityMap={viabilityMap}
              sizeFilter={sizeFilter}
              setSizeFilter={setSizeFilter}
              fetchTable={fetchTable}
              tableLoading={tableLoading}
              tableError={tableError}
              intactData={intactData}
              notIntactData={notIntactData}
              needsReviewData={needsReviewData}
              pageReview={pageReview}
              setPageReview={setPageReview}
              pageIntact={pageIntact}
              setPageIntact={setPageIntact}
              pageNotIntact={pageNotIntact}
              setPageNotIntact={setPageNotIntact}
              showIntact={showIntact}
              setShowIntact={setShowIntact}
              showNotIntact={showNotIntact}
              setShowNotIntact={setShowNotIntact}
              setIsRightBarOpen={setIsRightBarOpen}
              focusParticleByNumber={focusParticleByNumber}
            />
          )}
        </div>

        <RightSidebar
          isRightBarOpen={isRightBarOpen}
          setIsRightBarOpen={setIsRightBarOpen}
          showTable={showTable}
          viewScale={viewScale}
          setViewScale={setViewScale}
          resetView={resetView}
          ZOOM_MIN={ZOOM_MIN}
          ZOOM_MAX={ZOOM_MAX}
          setShowHelp={setShowHelp}
          selectedMethod={selectedMethod}
          setSelectedMethod={setSelectedMethod}
          onReanalyze={onReanalyze}
          onShapeClassify={onShapeClassify}
          sourceFile={sourceFile}
          loading={loading}
          descriptions={descriptions}
          infoOpen={infoOpen}
          infoPos={infoPos}
          toggleInfo={toggleInfo}
          openInfo={openInfo}
          closeInfo={closeInfo}
          setInfoOpen={setInfoOpen}
          isDrawingIntensity={isDrawingIntensity}
          startIntensityTool={startIntensityTool}
          minNm={minNm}
          showFilterPopup={showFilterPopup}
          handleFilterClick={handleFilterClick}
          showScalePopup={showScalePopup}
          handleSettingsClick={handleSettingsClick}
          handleTableClick={handleTableClick}
          showGrid={showGrid}
          setShowGrid={setShowGrid}
          imageId={imageId}
          onShapeGreen={() =>
            applySelectedParticlesAsShapeFeedback("green", "mark as intact")
          }
          onShapeRed={() =>
            applySelectedParticlesAsShapeFeedback("red", "mark as non intact")
          }
          onShapeSkip={() =>
            applySelectedParticlesAsShapeFeedback("skip", "ignore noise")
          }
          selectedCount={selectedIds.size}
          shapeEnabled={(!!sourceFile || !!imageId) && selectedIds.size > 0 && !loading}
        />
      </div>

      <FilterModal
        show={showFilterPopup}
        minNm={minNm}
        minNmInput={minNmInput}
        setMinNmInput={setMinNmInput}
        onCancel={() => setShowFilterPopup(false)}
        onSave={saveMinNm}
      />

      <ScaleModal
        show={showScalePopup}
        scale={scale}
        nmPerPixel={nmPerPixel}
        handleScaleField={handleScaleField}
        onCancel={() => setShowScalePopup(false)}
        onDrawLine={() => {
          setIsDrawingScale(true);
          setMode(null);
          setActive(null);
          showToastFn("Draw a line on the scale bar (click → drag → release)");
          setShowScalePopup(false);
        }}
        onRecalc={recalcDiametersWithScale}
        onSaveScale={async () => {
          await saveScaleToBackend();
          setShowScalePopup(false);
        }}
      />

      <HelpModal show={showHelp} onClose={() => setShowHelp(false)} />
    </>
  );
}

export default ImageCanvas;