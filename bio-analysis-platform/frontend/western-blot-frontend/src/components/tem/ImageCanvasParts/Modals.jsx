import React from "react";

export function LoadingOverlay({ loading }) {
  if (!loading) return null;
  const rows = Array.from({ length: 10 });

  return (
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

        <div className="loading-title">Processing TEM Image...</div>
        <div className="loading-subtitle">
          Please wait while the TEM analysis is running.
        </div>
      </div>
    </div>
  );
}

/** Modal for setting the 'Hide particles below' threshold (minimum 30 nm). */
export function FilterModal({
  show,
  minNm,
  minNmInput,
  setMinNmInput,
  onCancel,
  onSave,
}) {
  if (!show) return null;

  return (
    <div className="modalOverlay">
      <div className="modal">
        <h4 className="modalTitle">Hide particles below</h4>

        <div className="modalRow">
          <label className="modalLabel">
            Hide below (nm):
            <input
              className="input"
              type="number"
              min={30}
              value={minNmInput}
              onChange={(e) => setMinNmInput(e.target.value)}
            />
          </label>
        </div>

        <div className="modalHint">
          Minimum value is <b>30 nm</b>. Particles with diameter &lt; <b>{Number(minNmInput) || minNm} nm</b> will be hidden.
        </div>

        <div className="modalFooter">
          <button className="btn" onClick={onCancel}>
            Cancel
          </button>
          <button className="btn btn--primary" onClick={onSave}>
            Save
          </button>
        </div>
      </div>
    </div>
  );
}

export function ScaleModal({
  show,
  scale,
  nmPerPixel,
  handleScaleField,
  onCancel,
  onDrawLine,
  onRecalc,
  onSaveScale,
}) {
  if (!show) return null;

  return (
    <div className="modalOverlay">
      <div className="modal">
        <h4 className="modalTitle">Image Scale Settings</h4>

        <div className="modalRow">
          <label className="modalLabel">
            Real scale value:
            <input
              className="input"
              type="number"
              value={scale.value}
              onChange={(e) => handleScaleField("value", e.target.value)}
            />
          </label>

          <select
            className="select"
            value={scale.unit}
            onChange={(e) => handleScaleField("unit", e.target.value)}
          >
            <option value="nm">nm</option>
            <option value="um">µm</option>
          </select>
        </div>

        <div className="modalRow">
          <label className="modalLabel">
            Measured pixels (auto):
            <input className="input input--readonly" type="number" value={scale.px} readOnly />
          </label>
        </div>

        <div className="modalActions">
          <button className="btn" onClick={onDrawLine}>
            Draw scale line
          </button>

          <button className="btn btn--muted" onClick={onRecalc}>
            Recalc diameters
          </button>
        </div>

        <div className="modalHint">
          {nmPerPixel() ? (
            <>
              Current: <b>{nmPerPixel().toFixed(4)} nm / pixel</b>
            </>
          ) : (
            <>Set scale value and draw a line to calculate nm/pixel</>
          )}
        </div>

        <div className="modalFooter">
          <button className="btn" onClick={onCancel}>
            Cancel
          </button>
          <button className="btn btn--primary" onClick={onSaveScale}>
            Save Scale
          </button>
        </div>
      </div>
    </div>
  );
}

export function HelpModal({ show, onClose }) {
  if (!show) return null;

  return (
    <div className="modalOverlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h4 className="modalTitle">Controls & Shortcuts</h4>

        <div style={{ fontSize: 13, lineHeight: 1.6 }} className="modalBody">
          <div style={{ marginBottom: 10 }}>
            <b>Multi-select circles</b>
            <br />
            • Hold <b>Ctrl</b> + <b>Click</b> to select multiple circles
          </div>

          <div style={{ marginBottom: 10 }}>
            <b>Drag-box selection</b>
            <br />
            • Hold <b>Shift</b> + <b>Drag</b> to select circles inside a box
          </div>

          <div style={{ marginBottom: 10 }}>
            <b>Pan / Move image (when zoomed)</b>
            <br />
            • Hold <b>Ctrl</b> + <b>Space</b> + <b>Mouse Drag</b> to move (top/bottom/left/right)
          </div>

          <div style={{ marginBottom: 2, opacity: 0.75 }}>
            Tip: Zoom in first, then use pan to navigate.
          </div>
        </div>

        <div className="modalFooter">
          <button className="btn btn--primary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}