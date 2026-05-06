import { useState } from "react";
import "../../App.css";

type Props = {
  selectedFile: File | null;
  onFileChange: (file: File | null) => void;
  onAnalyze: () => void;
  loading: boolean;
  disabledAnalyze?: boolean;
  fetchAllImages: any;
};

function UploadPanel({
  selectedFile,
  onFileChange,
  loading,
}: Props) {
  const [isDragActive, setIsDragActive] = useState(false);
  const [showTips, setShowTips] = useState(false);

  const handleDragOver = (e: React.DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(true);
  };

  const handleDragEnter = (e: React.DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    e.stopPropagation();
    // Only deactivate when truly leaving the zone, not a child element
    if (!e.currentTarget.contains(e.relatedTarget as Node)) {
      setIsDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);
    const file = e.dataTransfer.files?.[0] ?? null;
    if (file) onFileChange(file);
  };

  if (!!selectedFile && !loading) return null;

  if (loading) {
    return (
      <div className="card card-elevated">
        <div className="upload-loading">
          <div className="wb-spinner" />
          <div className="upload-loading-title">Analyzing…</div>
          <div className="upload-loading-sub">Processing your blot image</div>
        </div>
      </div>
    );
  }

  return (
    <div className="card card-elevated">
      <input
        id="fileUpload"
        type="file"
        accept=".png,.jpg,.jpeg,.tif,.tiff"
        onChange={(e) => onFileChange(e.target.files?.[0] ?? null)}
        className="hidden-file-input"
      />

      <label
        htmlFor="fileUpload"
        className={`upload-zone${isDragActive ? " drag-active" : ""}`}
        onDragOver={handleDragOver}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <div className="upload-zone-icon">
          <svg
            width="44"
            height="44"
            viewBox="0 0 44 44"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <rect width="44" height="44" rx="12" fill="currentColor" fillOpacity="0.10" />
            <path
              d="M22 29V17M22 17L16 23M22 17L28 23"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <path
              d="M13 31H31"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
            />
          </svg>
        </div>

        <div className="upload-zone-title">
          {isDragActive ? "Release to upload" : "Drop your Western Blot image here"}
        </div>

        <div className="upload-zone-sub">
          or <span className="upload-zone-link">click to browse</span>
        </div>

        <div className="upload-zone-formats">
          PNG · JPG · TIFF supported
        </div>
      </label>

      <div className="upload-tips">
        <button
          className="upload-tips-toggle"
          onClick={(e) => { e.preventDefault(); setShowTips((p) => !p); }}
          type="button"
        >
          <span>Best Practices</span>
          <span className={`upload-tips-chevron${showTips ? " open" : ""}`}>▾</span>
        </button>
        {showTips && (
          <ul className="upload-tips-list">
            <li>Use 8-bit or 16-bit grayscale TIFF for best quantification accuracy</li>
            <li>Avoid over-exposed bands — saturation skews intensity measurements</li>
            <li>Place a molecular weight ladder in Lane 0 before other lanes</li>
            <li>Crop to the relevant blot area and remove film borders before uploading</li>
          </ul>
        )}
      </div>
    </div>
  );
}

export default UploadPanel;
