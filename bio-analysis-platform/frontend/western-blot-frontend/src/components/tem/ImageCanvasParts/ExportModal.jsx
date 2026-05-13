import React, { useState } from "react";

const FORMAT_OPTIONS = [
  {
    key: "pdf",
    label: "PDF Report",
    desc: "Annotated image + full particle table in a single PDF",
    icon: "📄",
  },
  {
    key: "excel",
    label: "Excel",
    desc: "Summary sheet + particle data table (diameter, status)",
    icon: "📊",
  },
  {
    key: "png",
    label: "PNG Image",
    desc: "Annotated image with particle circles at original resolution",
    icon: "🖼",
  },
];

export default function ExportModal({ show, onClose, onExport, imageName, isExporting }) {
  const [formats, setFormats] = useState({ pdf: true, excel: false, png: false });

  if (!show) return null;

  const anySelected = Object.values(formats).some(Boolean);

  const toggle = (key) =>
    setFormats((prev) => ({ ...prev, [key]: !prev[key] }));

  return (
    <div className="exportOverlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="exportModal">
        <div className="exportHeader">
          <div className="exportTitle">Export TEM Report</div>
          <button className="exportClose" onClick={onClose} disabled={isExporting}>
            ×
          </button>
        </div>

        <div className="exportBody">
          <div className="exportImageName">
            <span className="exportImageLabel">Image:</span>{" "}
            <span className="exportImageValue">{imageName || "—"}</span>
          </div>

          <div className="exportFormatsLabel">Select export format(s):</div>

          <div className="exportFormatList">
            {FORMAT_OPTIONS.map(({ key, label, desc, icon }) => (
              <label
                key={key}
                className={`exportFormatRow ${formats[key] ? "exportFormatRow--active" : ""}`}
              >
                <input
                  type="checkbox"
                  className="exportCheckbox"
                  checked={formats[key]}
                  onChange={() => toggle(key)}
                  disabled={isExporting}
                />
                <span className="exportFormatIcon">{icon}</span>
                <span className="exportFormatInfo">
                  <span className="exportFormatName">{label}</span>
                  <span className="exportFormatDesc">{desc}</span>
                </span>
              </label>
            ))}
          </div>
        </div>

        <div className="exportFooter">
          <button className="exportCancelBtn" onClick={onClose} disabled={isExporting}>
            Cancel
          </button>
          <button
            className="exportBtn"
            onClick={() => onExport(formats)}
            disabled={!anySelected || isExporting}
          >
            {isExporting ? (
              <span className="exportSpinner">Exporting…</span>
            ) : (
              "Export"
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
