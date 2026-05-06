import { useState, useCallback, useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import "../../App.css";
import type { Band } from "./BandTable";

type Props = {
  previewUrl: string;
  annotatedImageUrl: string;
  plotUrl: string;
  bands: Band[];
  selectedBandId: number | null;
  onSelectBand: (id: number) => void;
  imageWidth: number;
  imageHeight: number;
  onAddToReport?: (band: Band) => void;
  // NEW: manual band adding
  manualAddMode?: boolean;
  onManualBandAdd?: (x: number, y: number) => void;
};

type ContextMenu = {
  x: number;
  y: number;
  band: Band;
} | null;

function ImageViewer({
  previewUrl,
  annotatedImageUrl,
  plotUrl,
  bands,
  selectedBandId,
  onSelectBand,
  imageWidth,
  imageHeight,
  onAddToReport,
  manualAddMode = false,
  onManualBandAdd,
}: Props) {
  const [contextMenu, setContextMenu] = useState<ContextMenu>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);

  useEffect(() => {
    if (!contextMenu) return;
    const close = () => setContextMenu(null);
    document.addEventListener("click", close);
    document.addEventListener("scroll", close, true);
    return () => {
      document.removeEventListener("click", close);
      document.removeEventListener("scroll", close, true);
    };
  }, [contextMenu]);

  useEffect(() => {
    if (!contextMenu || !menuRef.current) return;
    const el = menuRef.current;
    const rect = el.getBoundingClientRect();
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    let { x, y } = contextMenu;
    if (x + rect.width > vw) x = vw - rect.width - 8;
    if (y + rect.height > vh) y = vh - rect.height - 8;
    el.style.left = `${x}px`;
    el.style.top = `${y}px`;
  }, [contextMenu]);

  const handleBandRightClick = useCallback(
    (e: React.MouseEvent, band: Band) => {
      e.preventDefault();
      e.stopPropagation();
      if (!manualAddMode) {
        setContextMenu({ x: e.clientX, y: e.clientY, band });
      }
    },
    [manualAddMode]
  );

  const handleAddToReport = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      if (contextMenu && onAddToReport) onAddToReport(contextMenu.band);
      setContextMenu(null);
    },
    [contextMenu, onAddToReport]
  );

  const handleSelectBand = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      if (contextMenu) onSelectBand(contextMenu.band.id);
      setContextMenu(null);
    },
    [contextMenu, onSelectBand]
  );

  // Handle click on image for manual band adding
  const handleImageClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (!manualAddMode || !onManualBandAdd || !imgRef.current) return;

      // Ignore if clicked on an existing dot
      const target = e.target as HTMLElement;
      if (target.classList.contains("image-dot")) return;

      const rect = imgRef.current.getBoundingClientRect();
      const clickX = e.clientX - rect.left;
      const clickY = e.clientY - rect.top;

      if (clickX < 0 || clickY < 0 || clickX > rect.width || clickY > rect.height) return;

      const safeW = imageWidth || imgRef.current.naturalWidth || 1;
      const safeH = imageHeight || imgRef.current.naturalHeight || 1;

      const x = Math.round((clickX / rect.width) * safeW);
      const y = Math.round((clickY / rect.height) * safeH);

      onManualBandAdd(x, y);
    },
    [manualAddMode, onManualBandAdd, imageWidth, imageHeight]
  );

  if (!previewUrl && !annotatedImageUrl && !plotUrl) return null;

  const currentImage = annotatedImageUrl || previewUrl;
  const safeWidth = imageWidth || 1;
  const safeHeight = imageHeight || 1;

  const contextMenuPortal = contextMenu
    ? createPortal(
        <div
          ref={menuRef}
          className="band-context-menu"
          style={{ position: "fixed", top: contextMenu.y, left: contextMenu.x, zIndex: 99999, backgroundColor: "white", border: "1px solid #ccc", borderRadius: 4, boxShadow: "0 2px 8px rgba(0,0,0,0.15)" }}
          onClick={(e) => e.stopPropagation()}
          onContextMenu={(e) => e.preventDefault()}
        >
          <div className="context-menu-header">
            {contextMenu.band.name} &nbsp;·&nbsp; Lane {contextMenu.band.lane} &nbsp;·&nbsp;{" "}
            {contextMenu.band.molecularWeight} kDa
          </div>
          {onAddToReport && (
            <button type="button" className="context-menu-item" onClick={handleAddToReport}>
              Add to Report
            </button>
          )}
          <button type="button" className="context-menu-item" onClick={handleSelectBand}>
            Select Band
          </button>
          <button
            type="button"
            className="context-menu-item context-menu-cancel"
            onClick={(e) => { e.stopPropagation(); setContextMenu(null); }}
          >
            Cancel
          </button>
        </div>,
        document.body
      )
    : null;

  return (
    <>
      <div className="card image-viewer-card card-elevated">
        {!previewUrl ? (
          <p className="error">No image uploaded yet.</p>
        ) : (
          <div className="image-section">
            {currentImage && (
              <div className="image-block">
                <div className="image-header-row">
                  <h3 className="image-title">Annotated Image</h3>
                  {plotUrl && (
                    <button
                      className="primary-btn"
                      onClick={() => window.open(plotUrl, "_blank")}
                      type="button"
                    >
                      Open 3D Intensity Graph
                    </button>
                  )}
                </div>

                {manualAddMode && (
                  <div className="manual-band-hint">
                    🖱️ Click anywhere on the image to add a manual band. kDa &amp; concentration
                    will be interpolated from nearby ladder bands.
                  </div>
                )}

                <div
                  className="image-overlay-wrap"
                  style={{ cursor: manualAddMode ? "crosshair" : "default" }}
                  onClick={handleImageClick}
                >
                  <img
                    ref={imgRef}
                    src={currentImage}
                    alt="Annotated"
                    className="preview-img"
                  />

                  <div className="image-dot-layer">
                    {bands.map((band) => (
                      <button
                        key={band.id}
                        type="button"
                        className={`image-dot ${selectedBandId === band.id ? "active" : ""} ${
                          (band as any).isManual ? "manual-dot" : ""
                        }`}
                        style={{
                          left: `${(band.x / safeWidth) * 100}%`,
                          top: `${(band.y / safeHeight) * 100}%`,
                        }}
                        onClick={(e) => {
                          e.stopPropagation();
                          if (!manualAddMode) onSelectBand(band.id);
                        }}
                        onContextMenu={(e) => handleBandRightClick(e, band)}
                        title={`${band.name} — ${band.molecularWeight} kDa${
                          (band as any).isManual ? " (manual)" : ""
                        }`}
                      />
                    ))}
                  </div>
                </div>

                {bands.length > 0 && onAddToReport && !manualAddMode && (
                  <p className="section-subtitle" style={{ marginTop: 6 }}>
                    Right-click any band dot to add it to the report.
                  </p>
                )}
              </div>
            )}

            {!annotatedImageUrl && plotUrl && (
              <div className="image-header-row">
                <div />
                <button
                  className="primary-btn"
                  onClick={() => window.open(plotUrl, "_blank")}
                  type="button"
                >
                  Open 3D Intensity Graph
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {contextMenuPortal}
    </>
  );
}

export default ImageViewer;