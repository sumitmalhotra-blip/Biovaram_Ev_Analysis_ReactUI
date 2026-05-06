import { useEffect, useMemo, useState } from "react";
import ImageCanvas from "./ImageCanvas";
import BoxPopup from "./Boxpopup";
import "./ImageCanvas.css";

import { TEM_API as API, STATIC_BASE } from "../../services/api";

/**
 * Renders an <img> that transparently handles TIFF files.
 * Browsers cannot natively render TIFF — this component decodes via UTIF on mount
 * and displays a PNG data URL instead.
 */
function TiffSafeImage({ src, alt, className }) {
  const [resolvedSrc, setResolvedSrc] = useState(src);

  useEffect(() => {
    if (!src) return;
    const lower = src.toLowerCase().split("?")[0];
    if (!lower.endsWith(".tif") && !lower.endsWith(".tiff")) {
      setResolvedSrc(src);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const UTIF = (await import("utif")).default;
        const res = await fetch(src);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const buf = await res.arrayBuffer();
        const ifds = UTIF.decode(buf);
        if (!ifds || !ifds.length) throw new Error("No TIFF frames");
        UTIF.decodeImage(buf, ifds[0]);
        const rgba = UTIF.toRGBA8(ifds[0]);
        const w = ifds[0].width;
        const h = ifds[0].height;
        const canvas = document.createElement("canvas");
        canvas.width = w;
        canvas.height = h;
        const ctx = canvas.getContext("2d");
        if (!ctx) throw new Error("No canvas context");
        const imgData = ctx.createImageData(w, h);
        imgData.data.set(rgba);
        ctx.putImageData(imgData, 0, 0);
        if (!cancelled) setResolvedSrc(canvas.toDataURL("image/png"));
      } catch (err) {
        console.error("[TEM] Thumbnail TIFF decode failed:", err);
      }
    })();
    return () => { cancelled = true; };
  }, [src]);

  return (
    <img
      src={resolvedSrc}
      alt={alt}
      className={className}
      onError={(e) => {
        e.target.onerror = null;
        e.target.style.opacity = "0.25";
        e.target.style.filter = "grayscale(1)";
      }}
    />
  );
}

const makeId = () => `${Date.now()}_${Math.random().toString(16).slice(2)}`;

function Tem() {
  const userId = 3;
  const [images, setImages] = useState([]);
  const [selectedImage, setSelectedImage] = useState(null);
  const [selectedBox, setSelectedBox] = useState(null);
  const [hoverId, setHoverId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [isUploading , setUpload] = useState(false);
  const [tableRefreshTick, setTableRefreshTick] = useState(0);
  const [query, setQuery] = useState("");
  const [formatFilter, setFormatFilter] = useState("all");
  const [toast, setToast] = useState(null);

  const [uploadedFileMap, setUploadedFileMap] = useState({});

  const rows = Array.from({ length: 10 });

  const showToastFn = (message) => {
  setToast(message);
  };

  const normalizeApiImagePath = (url) => {
    const value = String(url || "").trim();
    if (!value) return "";

    if (value.startsWith("http://") || value.startsWith("https://")) {
      try {
        const u = new URL(value);
        return `${u.pathname}${u.search}${u.hash}`;
      } catch {
        return value.replace(STATIC_BASE, "");
      }
    }

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

  const toAbsoluteImageUrl = (url) => {
    const clean = normalizeApiImagePath(url);
    if (!clean) return "";
    if (clean.startsWith("http://") || clean.startsWith("https://")) return clean;
    return `${STATIC_BASE}${clean}`;
  };

  const normalizeBoxArray = (arr) =>
    (Array.isArray(arr) ? arr : []).map((b) => ({
      id: b.id || makeId(),
      ...b,
      cx: b.cx ?? b.x,
      cy: b.cy ?? b.y,
    }));

  const safeFetch = async (url, options = {}) => {
    const res = await fetch(url, options);

    if (!res.ok) {
      throw new Error("Something went wrong: " + res.status);
    }

    const text = await res.text();

    try {
      return text ? JSON.parse(text) : {};
    } catch {
      throw new Error("Invalid JSON from server");
    }
  };

  /** Syncs the full circle list for an image to the backend and triggers a table refresh. */
  const syncCirclesToBackend = async (imageId, boxes) => {
    try {
      const payload = (Array.isArray(boxes) ? boxes : []).map((b) => ({
        number: b.number ?? null,
        x: Number(b.x ?? b.cx),
        y: Number(b.y ?? b.cy),
        r: Number(b.r ?? 30),
        diameter_nm: b.diameter_nm ?? null,
        viability: b.viability ?? "needs_review",
      }));

      await safeFetch(`${API}/images/${userId}/${imageId}/circles`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      setTableRefreshTick((t) => t + 1);
    } catch (e) {
      console.error("syncCirclesToBackend error:", e);
      showToastFn("Failed to save changes");
    }
  };

  const getImageName = (url) => {
    if (!url) return "";
    const fileName = url.split("/").pop();
    const namePart = fileName.split("_").slice(1).join("_");
    return namePart.replace(/\.[^/.]+$/, "");
  };

  const getExt = (url) => {
    const u = String(url || "").toLowerCase();
    const clean = u.split("?")[0].split("#")[0];
    const parts = clean.split(".");
    if (parts.length < 2) return "";
    return parts.pop();
  };

  /** Fetches all images for the current user and populates the sidebar list. */
  const fetchImages = async () => {
    if (!userId) return;
      setLoading(true)
    try {
      const res = await fetch(`${API}/images/${userId}`);

      if (!res.ok) {
        throw new Error("Failed: " + res.status);
      }

      const text = await res.text();
      let data;

      try {
        data = text ? JSON.parse(text) : {};
      } catch {
        throw new Error("Invalid JSON");
      }

      if (!data || typeof data !== "object") {
        throw new Error("Wrong data format");
      }

      const list = Object.entries(data).map(([id, img]) => {
        const relativeImageUrl = normalizeApiImagePath(img.image_url);
        const relativeOriginalUrl = normalizeApiImagePath(img.original_image_url);

        return {
          image_id: id,
          image_url: relativeImageUrl,
          image_name: getImageName(relativeOriginalUrl || relativeImageUrl),
          boxes: normalizeBoxArray(img.boxes),
          scale: img.scale || null,
        };
      });

      setImages(list);

      if (list.length > 0 && !selectedImage) {
        setSelectedImage({
          image_id: list[0].image_id,
          image_url: list[0].image_url,
          boxes: JSON.parse(JSON.stringify(list[0].boxes)),
          scale: JSON.parse(JSON.stringify(list[0].scale)),
        });
      }
      setLoading(false)
    } catch (err) {
      console.error(err);
      showToastFn("Failed to load images");
    }
  };

  useEffect(() => {
    // Auto-recover orphaned files on mount, then refresh the list
    fetch(`${API}/recover-images/${userId}`, { method: "POST" })
      .then(() => fetchImages())
      .catch(() => fetchImages());
  }, [userId]);

  const recoverImages = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/recover-images/${userId}`, { method: "POST" });
      const data = await res.json();
      showToastFn(`Recovered ${data.recovered} image(s), removed ${data.purged} stale record(s)`);
      await fetchImages();
    } catch (err) {
      console.error(err);
      showToastFn("Recovery failed");
    } finally {
      setLoading(false);
    }
  };

  const MAX_FILE_SIZE = 5 * 1024 * 1024;
  const MAX_FILES = 5;
  const ALLOWED_TYPES = [
    "image/png",
    "image/jpeg",
    "image/tiff",
    "image/tif",
    "application/octet-stream",
  ];

  /** Handles file selection, validates types/sizes, uploads to the backend, and refreshes the image list. */
  const uploadImage = async (e) => {
    const files = Array.from(e.target.files || []);

    if (!files.length) return;

    if (files.length > MAX_FILES) {
      alert(`Max ${MAX_FILES} files allowed`);
      return;
    }

    for (let file of files) {
      if (!ALLOWED_TYPES.includes(file.type)) {
        alert(`Invalid file: ${file.name}`);
        return;
      }

      if (file.size > MAX_FILE_SIZE) {
        alert(`File too large: ${file.name}`);
        return;
      }
    }

    setLoading(true);
    setUpload(true);

    try {
      const formData = new FormData();
      files.forEach((f) => formData.append("files", f));

      const data = await safeFetch(`${API}/upload-multiple-images/${userId}`, {
        method: "POST",
        body: formData,
      });

      const normalized = (data || []).map((img) => {
        const relativeImageUrl = normalizeApiImagePath(img.image_url);
        const relativeOriginalUrl = normalizeApiImagePath(img.original_image_url);

        return {
          ...img,
          image_url: relativeImageUrl,
          image_name: getImageName(relativeOriginalUrl || relativeImageUrl),
          boxes: normalizeBoxArray(img.boxes),
          scale: img.scale || null,
        };
      });

      const nextFileMap = {};
      normalized.forEach((img, index) => {
        if (files[index]) {
          nextFileMap[img.image_id] = files[index];
        }
      });

      setUploadedFileMap((prev) => ({ ...prev, ...nextFileMap }));
      setImages((prev) => [...normalized, ...prev]);

      if (normalized.length > 0) {
        setSelectedImage({
          image_id: normalized[0].image_id,
          image_url: normalized[0].image_url,
          boxes: JSON.parse(JSON.stringify(normalized[0].boxes || [])),
          scale: JSON.parse(JSON.stringify(normalized[0].scale || null)),
        });
      }

      await fetchImages();
    } catch (err) {
      console.error(err);
      showToastFn("Upload failed. Please try again.");
    } finally {
      setLoading(false);
      setUpload(false);
      e.target.value = "";
    }
  };

  const handleCreateCircle = (x, y) => {
    if (!selectedImage) return;

    const r = 20;
    const circle = {
      id: makeId(),
      cx: x,
      cy: y,
      x,
      y,
      r,
      diameter_nm: null,
      viability: "needs_review",
      number: null,
    };

    const nextBoxes = [...(selectedImage.boxes || []), circle];

    setSelectedImage((prev) => ({ ...prev, boxes: nextBoxes }));

    setImages((prev) =>
      prev.map((i) =>
        i.image_id === selectedImage.image_id ? { ...i, boxes: nextBoxes } : i
      )
    );

    syncCirclesToBackend(selectedImage.image_id, nextBoxes);
  };

  const handleSaveCircle = (updated) => {
    if (!selectedBox || !selectedImage) return;

    if (updated === null) {
      const nextBoxes = selectedImage.boxes.filter((b) => b.id !== selectedBox.id);

      setSelectedImage((prev) => ({ ...prev, boxes: nextBoxes }));
      setImages((prev) =>
        prev.map((i) =>
          i.image_id === selectedImage.image_id ? { ...i, boxes: nextBoxes } : i
        )
      );
      setSelectedBox(null);
      syncCirclesToBackend(selectedImage.image_id, nextBoxes);
      return;
    }

    const nextBoxes = (selectedImage.boxes || []).map((b) =>
      b.id === updated.id ? updated : b
    );

    setSelectedImage((prev) => ({ ...prev, boxes: nextBoxes }));
    setImages((prev) =>
      prev.map((i) =>
        i.image_id === selectedImage.image_id ? { ...i, boxes: nextBoxes } : i
      )
    );
    setSelectedBox(null);

    syncCirclesToBackend(selectedImage.image_id, nextBoxes);
  };

  const handleLiveChangeCircle = (live) => {
    if (!live || !selectedImage) return;

    const nextBoxes = (selectedImage.boxes || []).map((b) =>
      b.id === live.id ? live : b
    );

    setSelectedImage((prev) => ({ ...prev, boxes: nextBoxes }));
    setImages((prev) =>
      prev.map((i) =>
        i.image_id === selectedImage.image_id ? { ...i, boxes: nextBoxes } : i
      )
    );

    setSelectedBox(live);
  };

  const handleDeleteImage = async (imageId) => {
    if (!userId || !imageId) return;

    const ok = window.confirm("Delete this image?");
    if (!ok) return;

    try {
      await safeFetch(`${API}/images/${userId}/${imageId}`, {
        method: "DELETE",
      });

      setImages((prev) => prev.filter((img) => img.image_id !== imageId));

      setUploadedFileMap((prev) => {
        const copy = { ...prev };
        delete copy[imageId];
        return copy;
      });

      if (selectedImage?.image_id === imageId) {
        setSelectedImage(null);
      }
    } catch (e) {
      console.error(e);
      showToastFn("Delete failed");
    }
  };

  const getCounts = (img) => {
    const bs = img?.boxes || [];
    let intact = 0;
    let notIntact = 0;
    let needs = 0;

    for (const b of bs) {
      const v = b?.viability;
      if (v === "intact" || v === "viable") intact++;
      else if (v === "not_intact" || v === "non_viable") notIntact++;
      else needs++;
    }

    return { total: bs.length, intact, notIntact, needs };
  };

  const filteredImages = useMemo(() => {
    const q = query.trim().toLowerCase();

    const matchesQuery = (img) => {
      if (!q) return true;
      const idMatch = String(img.image_id).toLowerCase().includes(q);
      const urlMatch = String(img.image_url || "").toLowerCase().includes(q);
      const nameMatch = String(img.image_name || "").toLowerCase().includes(q);
      return idMatch || urlMatch || nameMatch;
    };

    const matchesFormat = (img) => {
      if (formatFilter === "all") return true;
      const ext = getExt(img.image_url);
      if (formatFilter === "jpg") return ext === "jpg" || ext === "jpeg";
      if (formatFilter === "png") return ext === "png";
      if (formatFilter === "tiff") return ext === "tif" || ext === "tiff";
      return true;
    };

    return (images || []).filter((img) => matchesQuery(img) && matchesFormat(img));
  }, [images, query, formatFilter]);

  /** Selects an image from the sidebar and loads it into the canvas view. */
  const selectImage = (img) => {
    setSelectedImage({
      image_id: img.image_id,
      image_url: normalizeApiImagePath(img.image_url),
      boxes: (JSON.parse(JSON.stringify(img.boxes || [])) || []).map((b) => ({
        id: b.id || makeId(),
        ...b,
        cx: b.cx ?? b.x,
        cy: b.cy ?? b.y,
      })),
      scale: JSON.parse(JSON.stringify(img.scale)),
    });
  };

  const canUseShapeApi = !!uploadedFileMap[selectedImage?.image_id];

  return (
    <div className="temRoot">
      <div className="temSidebar">
        <div className="temSidebarHeader">
          <div className="temHeaderRow">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search image id/name..."
              className="temSearchInput"
            />

            <label className="temUploadBtn" title="Upload images">
              + Upload
              <input
                type="file"
                multiple
                accept="image/png, image/jpeg, image/tiff"
                hidden
                onChange={uploadImage}
              />
            </label>
            <button
              className="temRecoverBtn"
              title="Recover images that exist on disk but are missing from the list"
              onClick={recoverImages}
            >
              ↺ Recover
            </button>
          </div>
        </div>

        <div className="temListWrap">
          {!images || images.length === 0 ? (
            <div className="temEmptyImages">
              <div className="temEmptyIcon">🖼️</div>
              <div className="temEmptyTitle">No Images Yet</div>
              <div className="temEmptySub">
                Click <span className="temLinkText">+ Upload</span> to add your TEM
                images and start analyzing particles.
              </div>
              <div className="temHintPill">Supports JPG / PNG / TIFF</div>
            </div>
          ) : filteredImages.length === 0 ? (
            <div className="temNoResults">No results found for “{query}”.</div>
          ) : (
            filteredImages.map((img) => {
              const isSelected = selectedImage?.image_id === img.image_id;
              const c = getCounts(img);

              return (
                <div
                  key={img.image_id}
                  onMouseEnter={() => setHoverId(img.image_id)}
                  onMouseLeave={() => setHoverId(null)}
                  onClick={() => selectImage(img)}
                  className={`temImageCard ${isSelected ? "isSelected" : ""}`}
                >
                  <TiffSafeImage src={toAbsoluteImageUrl(img.image_url)} alt="" className="temThumb" />

                  <div className="temCardBody">
                    <div className="temImageName">Image {img.image_name}</div>

                    <div className="temPillRow">
                      <span className="temPill temPillOk">✅ {c.intact}</span>
                      <span className="temPill temPillBad">❌ {c.notIntact}</span>
                      <span className="temPill temPillWarn">⚠ {c.needs}</span>
                      <span className="temPill temPillNeutral">Circles: {c.total}</span>
                    </div>

                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteImage(img.image_id);
                      }}
                      title="Delete image"
                      className="temDeleteBtn"
                    >
                      🗑
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {loading && (
          <div className="loading-overlay">
            <div className="loading-card">
              <div className="dna-loader">
                {rows.map((_, i) => (
                  <div
                    key={i}
                    className="dna-row"
                    style={{ animationDelay: `${i * 0.12}s` }}
                  >
                    <span className="dna-dot dna-dot-left"></span>
                    <span className="dna-bridge"></span>
                    <span className="dna-dot dna-dot-right"></span>
                  </div>
                ))}
              </div>

             {isUploading  &&  <div className="loading-title">Uploading Image...</div> }
              <div className="loading-subtitle">
                Please wait while the TEM analysis is running.
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="temRightPanel" data-scroll="rightpanel">
        <div className="temRightInner">
          {selectedImage ? (
            <>
              <ImageCanvas
                imageId={selectedImage.image_id}
                imageUrl={selectedImage?.image_url}
                boxes={selectedImage.boxes}
                scale={selectedImage.scale}
                tableRefreshTick={tableRefreshTick}
                setScale={(scale) => {
                  setSelectedImage((prev) => ({ ...prev, scale }));
                  setImages((prev) =>
                    prev.map((i) =>
                      i.image_id === selectedImage.image_id ? { ...i, scale } : i
                    )
                  );
                }}
                setBoxes={(next) => {
                  const resolveNext = (prevArr) =>
                    typeof next === "function" ? next(prevArr) : next;

                  setSelectedImage((prev) => {
                    const prevArr = Array.isArray(prev?.boxes) ? prev.boxes : [];
                    const resolved = resolveNext(prevArr);

                    const arr = Array.isArray(resolved)
                      ? resolved
                      : Array.isArray(resolved?.boxes)
                      ? resolved.boxes
                      : [];

                    const safeArr = arr.map((b) => ({
                      id: b.id || makeId(),
                      ...b,
                      cx: b.cx ?? b.x,
                      cy: b.cy ?? b.y,
                    }));

                    setImages((imgs) =>
                      imgs.map((i) =>
                        i.image_id === prev.image_id ? { ...i, boxes: safeArr } : i
                      )
                    );

                    return { ...prev, boxes: safeArr };
                  });
                }}
                onCreateBox={handleCreateCircle}
                onSelectBox={setSelectedBox}
                sourceFile={uploadedFileMap[selectedImage.image_id] || null}
                canUseShapeApi={canUseShapeApi}
                setExternalImageUrl={(newImageUrl) => {
                  const cleanUrl = normalizeApiImagePath(newImageUrl);

                  setSelectedImage((prev) => {
                    if (!prev) return prev;

                    const updated = {
                      ...prev,
                      image_url: cleanUrl,
                    };

                    setImages((imgs) =>
                      imgs.map((i) =>
                        i.image_id === prev.image_id
                          ? { ...i, image_url: cleanUrl }
                          : i
                      )
                    );

                    return updated;
                  });
                }}
                onShapeApiResult={(data) => {
                  console.log("Shape API result:", data);
                  showToastFn(
                    `Shape API done: ${data?.counts?.total ?? 0} particles`
                  );
                }}
              />
            </>
          ) : (
            <div className="temSelectEmpty">
              <div className="temSelectEmptyInner">
                <svg
                  width="220"
                  height="160"
                  viewBox="0 0 220 160"
                  className="temEmptySvg"
                >
                  <rect x="20" y="18" width="180" height="120" rx="16" className="temSvgFrame" />
                  <path d="M40 120 L85 70 L120 105 L150 85 L180 120 Z" className="temSvgMountain" />
                  <circle cx="70" cy="52" r="10" className="temSvgSun" />
                  <circle cx="165" cy="48" r="4" className="temSvgDot" />
                  <circle cx="178" cy="48" r="4" className="temSvgDot" />
                  <circle cx="191" cy="48" r="4" className="temSvgDot" />
                  <path d="M110 142 C110 130 110 130 110 124" className="temSvgArrowLine" />
                  <path d="M103 132 L110 142 L117 132" className="temSvgArrowHead" />
                </svg>

                <div className="temSelectTitle">Select an image to start</div>

                <div className="temSelectSub">
                  Choose an image from the left sidebar or click{" "}
                  <span className="temSelectLink">+ Upload</span> to add new TEM
                  images.
                </div>

                {!toast && <div className="temTipPill">Tip: Upload TIFF for best quality</div>}
                {toast && <div className="temToast">{toast}</div>}
              </div>
            </div>
          )}
        </div>
      </div>

      {selectedBox && (
        <BoxPopup
          box={selectedBox}
          onClose={() => setSelectedBox(null)}
          onSave={handleSaveCircle}
          onChange={handleLiveChangeCircle}
        />
      )}
    </div>
  );
}

export default Tem;