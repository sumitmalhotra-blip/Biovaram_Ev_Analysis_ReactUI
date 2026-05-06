import { useState } from "react";
import axios from "axios";
import UploadPanel from "./UploadPanel";
import ImageViewer from "./ImageViewer";
import BandTable, { type Band } from "./BandTable";
import RulerMarker from "./RulerMarker";
import ReportTable from "./ReportTable";
import "./WesternModule.css";
import "../../App.css";
import { useEffect } from "react";

import { WESTERN_API as API_BASE, STATIC_BASE } from "../../services/api";

type AnalyzeResponse = {
  status?: string;
  band_count?: number;
  annotated_image?: string;
  csv_file?: string;
  plot_url?: string;
  bands?: Band[];
  image_width?: number;
  image_height?: number;
  error?: string;
};

type DetectRulerBandsResponse = {
  status?: string;
  lane_x?: number;
  ruler_bands?: RulerMark[];
  error?: string;
};

type SimpleMark = {
  x: number;
  y: number;
};

type RulerMark = {
  id: number;
  x: number;
  y: number;
  kda: string;
  concentration: string;
};

// ─── Interpolation helpers ────────────────────────────────────────────────────

/**
 * Interpolates molecular weight (kDa) and concentration for a clicked Y position
 * using logarithmic interpolation between the two nearest ladder bands.
 */
function interpolateBandValues(
  ladderBands: Band[],
  clickY: number,
  imageHeight: number
): { molecularWeight: string; concentration: string } {
  const sorted = [...ladderBands].sort((a, b) => a.y - b.y);

  if (!sorted.length) return { molecularWeight: "?", concentration: "?" };

  if (clickY <= sorted[0].y) {
    return {
      molecularWeight: String(sorted[0].molecularWeight),
      concentration: String(sorted[0].concentration),
    };
  }
  if (clickY >= sorted[sorted.length - 1].y) {
    const last = sorted[sorted.length - 1];
    return {
      molecularWeight: String(last.molecularWeight),
      concentration: String(last.concentration),
    };
  }

  let lower = sorted[0];
  let upper = sorted[sorted.length - 1];
  for (let i = 0; i < sorted.length - 1; i++) {
    if (sorted[i].y <= clickY && sorted[i + 1].y >= clickY) {
      lower = sorted[i];
      upper = sorted[i + 1];
      break;
    }
  }

  const t = (clickY - lower.y) / (upper.y - lower.y);

  const kdaLower = parseFloat(String(lower.molecularWeight));
  const kdaUpper = parseFloat(String(upper.molecularWeight));
  let kda = "?";
  if (
    Number.isFinite(kdaLower) &&
    Number.isFinite(kdaUpper) &&
    kdaLower > 0 &&
    kdaUpper > 0
  ) {
    const logKda =
      Math.log(kdaLower) + t * (Math.log(kdaUpper) - Math.log(kdaLower));
    kda = Math.round(Math.exp(logKda)).toString();
  }

  const concLower = parseFloat(String(lower.concentration));
  const concUpper = parseFloat(String(upper.concentration));
  let conc = "?";
  if (Number.isFinite(concLower) && Number.isFinite(concUpper)) {
    conc = (concLower + t * (concUpper - concLower)).toFixed(3);
  }

  return { molecularWeight: kda, concentration: conc };
}

function WesternModule() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string>("");
  const [annotatedImageUrl, setAnnotatedImageUrl] = useState<string>("");
  const [plotUrl, setPlotUrl] = useState<string>("");
  const [bands, setBands] = useState<Band[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [analyze, setanalyze] = useState<boolean>(false);
  const [error, setError] = useState<string>("");

  const [lane0MarkMode, setLane0MarkMode] = useState<boolean>(false);
  const [lane0TopBottomMarks, setLane0TopBottomMarks] = useState<SimpleMark[]>([]);
  const [rulerMarks, setRulerMarks] = useState<RulerMark[]>([]);

  const [selectedBandId, setSelectedBandId] = useState<number | null>(null);
  const [imageWidth, setImageWidth] = useState<number>(0);
  const [imageHeight, setImageHeight] = useState<number>(0);

  const [showPopup, setShowPopup] = useState(false);
  const [allImages, setAllImages] = useState<any[]>([]);
  const [popupThumbnails, setPopupThumbnails] = useState<Record<number, string>>({});
  const [lastServerImageUrl, setLastServerImageUrl] = useState<string>("");

  const [reportBands, setReportBands] = useState<Band[]>([]);
  const [showReport, setShowReport] = useState<boolean>(false);

  const [manualAddMode, setManualAddMode] = useState(false);
  const [manualBandCounter, setManualBandCounter] = useState(1);

  useEffect(() => {
    // fetchLastImage();
  }, []);

  useEffect(() => {
    return () => {
      if (previewUrl && previewUrl.startsWith("blob:")) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  // ─── TIFF support ─────────────────────────────────────────────────────────
  /**
   * Decodes a TIFF File into a PNG data URL using the UTIF library.
   * Required because browsers cannot natively render TIFF in <img> or canvas elements.
   */
  const decodeTiffToDataUrl = async (file: File): Promise<string> => {
    const UTIF = (await import("utif")).default;
    const arrayBuffer = await file.arrayBuffer();
    const ifds = UTIF.decode(arrayBuffer);
    if (!ifds || ifds.length === 0)
      throw new Error("Could not decode TIFF: no image frames found.");
    UTIF.decodeImage(arrayBuffer, ifds[0]);
    const rgba = UTIF.toRGBA8(ifds[0]);
    const width = ifds[0].width as number;
    const height = ifds[0].height as number;
    let canvas: HTMLCanvasElement | OffscreenCanvas;
    let ctx: CanvasRenderingContext2D | OffscreenCanvasRenderingContext2D | null;
    if (typeof OffscreenCanvas !== "undefined") {
      canvas = new OffscreenCanvas(width, height);
      ctx = (canvas as OffscreenCanvas).getContext("2d");
    } else {
      canvas = document.createElement("canvas");
      (canvas as HTMLCanvasElement).width = width;
      (canvas as HTMLCanvasElement).height = height;
      ctx = (canvas as HTMLCanvasElement).getContext("2d");
    }
    if (!ctx) throw new Error("Could not get canvas 2D context.");
    const imageData = ctx.createImageData(width, height);
    imageData.data.set(rgba);
    ctx.putImageData(imageData, 0, 0);
    if (canvas instanceof OffscreenCanvas) {
      const blob = await canvas.convertToBlob({ type: "image/png" });
      return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result as string);
        reader.onerror = () => reject(new Error("FileReader failed"));
        reader.readAsDataURL(blob);
      });
    } else {
      return (canvas as HTMLCanvasElement).toDataURL("image/png");
    }
  };

  /** Returns a browser-renderable URL: decodes TIFF to PNG data URL, passes other formats through unchanged. */
  const loadImageWithTiffSupport = async (url: string): Promise<string> => {
    const lower = url.toLowerCase();
    if (lower.endsWith(".tif") || lower.endsWith(".tiff")) {
      const res = await fetch(url);
      const blob = await res.blob();
      const file = new File([blob], "image.tif");
      return await decodeTiffToDataUrl(file);
    }
    return url;
  };

  const fetchFileFromUrl = async (url: string, filename: string): Promise<File> => {
    const res = await fetch(url);
    const blob = await res.blob();
    return new File([blob], filename);
  };

  const fetchLastImage = async () => {
    try {
      const res = await axios.get(`${API_BASE}/last`);
      const data = res.data;
      if (data.image_url) {
        const url = `${STATIC_BASE}${data.image_url}`;
        setLastServerImageUrl(url);
        const decoded = await loadImageWithTiffSupport(url);
        setPreviewUrl(decoded);
      }
      setSelectedFile(null);
      setLane0TopBottomMarks([]);
      setRulerMarks([]);
      setBands([]);
    } catch (err) {
      console.log("No previous image");
    }
  };

  /** Fetches all previously uploaded Western Blot images and loads their thumbnails into the gallery popup. */
  const fetchAllImages = async () => {
    try {
      const res = await axios.get(`${API_BASE}/all`);
      const images = res.data.images || [];
      setAllImages(images);
      setShowPopup(true);
      const thumbnails: Record<number, string> = {};
      await Promise.all(
        images.map(async (img: any) => {
          const url = `${STATIC_BASE}${img.image_url}`;
          try {
            thumbnails[img.id] = await loadImageWithTiffSupport(url);
          } catch {
            thumbnails[img.id] = url;
          }
        })
      );
      setPopupThumbnails(thumbnails);
    } catch (err) {
      console.error(err);
    }
  };

  /** Deletes a Western Blot image from the server by ID and refreshes the gallery. */
  const deleteImage = async (id: number) => {
    try {
      await axios.delete(`${API_BASE}/${id}`);
      fetchAllImages();
      // fetchLastImage();
    } catch (err) {
      console.error(err);
    }
  };

  /** Loads a previously saved image from the gallery into the analysis view. */
  const selectImage = async (img: any) => {
    const url = `${STATIC_BASE}${img.image_url}`;
    setLastServerImageUrl(url);
    const decoded = await loadImageWithTiffSupport(url);
    setPreviewUrl(decoded);
    setSelectedFile(null);
    setLane0TopBottomMarks([]);
    setRulerMarks([]);
    setBands([]);
    setAnnotatedImageUrl("");
    setPlotUrl("");
    setanalyze(false);
    setShowPopup(false);
    setManualAddMode(false);
  };

  /** Validates the selected file type, uploads it to the backend, and sets the preview image. */
  const handleFileChange = async (file: File | null) => {
    if (!file) return;
    const fileName = file.name.toLowerCase();
    const validExtension =
      fileName.endsWith(".png") ||
      fileName.endsWith(".jpg") ||
      fileName.endsWith(".jpeg") ||
      fileName.endsWith(".tif") ||
      fileName.endsWith(".tiff");
    if (!validExtension) {
      setError("Only PNG, JPG, JPEG, TIF, TIFF files are supported.");
      return;
    }
    setError("");
    setSelectedFile(file);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const response = await fetch(`${API_BASE}/upload`, {
        method: "POST",
        body: formData,
      });
      const data = await response.json();
      if (data.error) {
        setError(data.error);
        return;
      }
      const imageUrl = `${STATIC_BASE}${data.image_url}`;
      setLastServerImageUrl(imageUrl);
      const url = await loadImageWithTiffSupport(imageUrl);
      setPreviewUrl(url);
      setSelectedFile(null);
    } catch (err) {
      console.error("Preview error:", err);
      setError("Failed to preview the image. The file may be corrupted.");
      return;
    }
    setAnnotatedImageUrl("");
    setPlotUrl("");
    setBands([]);
    setLane0MarkMode(false);
    setLane0TopBottomMarks([]);
    setRulerMarks([]);
    setSelectedBandId(null);
    setImageWidth(0);
    setImageHeight(0);
    setanalyze(false);
    setManualAddMode(false);
    setManualBandCounter(1);
  };

  /** Returns the active image file: uses the in-memory selected file or re-fetches from server URL. */
  const getFileForApi = async (): Promise<File | null> => {
    if (selectedFile) return selectedFile;
    if (lastServerImageUrl) {
      const filename = lastServerImageUrl.split("/").pop() || "image.png";
      return await fetchFileFromUrl(lastServerImageUrl, filename);
    }
    return null;
  };

  // ─── Lane 0 marking ───────────────────────────────────────────────────────
  /**
   * Called by RulerMarker with coordinates already scaled to natural image pixels.
   * We send them directly to the backend — no additional scaling needed.
   */
  const handleAddLane0Mark = async (x: number, y: number) => {
    const updatedMarks = [...lane0TopBottomMarks, { x, y }].slice(0, 2);
    setLane0TopBottomMarks(updatedMarks);

    // Wait until both top and bottom are marked
    if (updatedMarks.length !== 2) return;

    try {
      setLoading(true);
      setError("");

      const file = await getFileForApi();
      if (!file) {
        setError("No image available. Please upload an image first.");
        setLoading(false);
        return;
      }

      const topY    = updatedMarks[0].y;
      const bottomY = updatedMarks[1].y;

      // Guard: top must be above bottom (smaller Y = higher on image)
      const minY = Math.min(topY, bottomY);
      const maxY = Math.max(topY, bottomY);

      if (maxY - minY < 5) {
        setError("Top and bottom marks are too close. Please select a wider range covering all ruler bands.");
        setLoading(false);
        return;
      }

      const formData = new FormData();
      formData.append("file", file);
      formData.append("ruler_lane", "0");
      formData.append("top_mark_y",    String(minY));
      formData.append("bottom_mark_y", String(maxY));

      const response = await axios.post<DetectRulerBandsResponse>(
        `${API_BASE}/detect-ruler-bands`,
        formData,
        { headers: { "Content-Type": "multipart/form-data" } }
      );

      const result = response.data;

      if (result.error) {
        setError(result.error);
        // Reset marks so user can try again
        setLane0TopBottomMarks([]);
        setRulerMarks([]);
        return;
      }

      if (!result.ruler_bands || result.ruler_bands.length === 0) {
        setError("No ruler bands detected in the selected range. Try widening your selection.");
        setLane0TopBottomMarks([]);
        setRulerMarks([]);
        return;
      }

      setRulerMarks(result.ruler_bands);
      setLane0MarkMode(false);

    } catch (err: any) {
      console.error("detect-ruler-bands error:", err);

      // Extract the most useful error message from axios response
      const serverMsg =
        err?.response?.data?.error ||
        err?.response?.data?.detail ||
        err?.message ||
        "Failed to detect ruler bands.";

      setError(`Error: ${serverMsg}`);

      // Let the user retry by resetting marks
      setLane0TopBottomMarks([]);
      setRulerMarks([]);
    } finally {
      setLoading(false);
    }
  };

  /** Updates the kDa value for a specific ruler mark by ID. */
  const handleKdaChange = (id: number, value: string) => {
    setRulerMarks((prev) =>
      prev.map((mark) => (mark.id === id ? { ...mark, kda: value } : mark))
    );
  };

  /** Updates the concentration value for a specific ruler mark by ID. */
  const handleConcentrationChange = (id: number, value: string) => {
    setRulerMarks((prev) =>
      prev.map((mark) => (mark.id === id ? { ...mark, concentration: value } : mark))
    );
  };

  /** Resets all lane 0 marks, ruler marks, bands, and analysis state for a fresh start. */
  const handleResetLane0 = () => {
    setLane0TopBottomMarks([]);
    setRulerMarks([]);
    setBands([]);
    setAnnotatedImageUrl("");
    setPlotUrl("");
    setError("");
    setSelectedBandId(null);
    setImageWidth(0);
    setImageHeight(0);
    setanalyze(false);
    setManualAddMode(false);
    setManualBandCounter(1);
  };

  /** Validates that at least 2 ruler marks exist with strictly descending positive kDa values. */
  const areRulerValuesValid = () => {
    if (rulerMarks.length < 2) return false;
    const values = rulerMarks.map((m) => Number(m.kda));
    if (values.some((v) => Number.isNaN(v) || v <= 0)) return false;
    // Must be strictly descending (top band = highest kDa)
    for (let i = 1; i < values.length; i++) {
      if (values[i] >= values[i - 1]) return false;
    }
    return true;
  };

  const canAnalyze =
    lane0TopBottomMarks.length === 2 &&
    rulerMarks.length > 0 &&
    rulerMarks.every(
      (mark) =>
        String(mark.kda || "").trim() !== "" &&
        String(mark.concentration || "").trim() !== ""
    ) &&
    areRulerValuesValid();

  /**
   * Submits the image and ruler marks to the backend for full band analysis.
   * Returns annotated image URL, band data, and concentration plot.
   */
  const handleAnalyze = async () => {
    if (!canAnalyze) {
      setError(
        "Please mark lane 0 range and enter all ruler kDa values in strictly descending order (e.g. 180, 130, 100…)."
      );
      return;
    }
    try {
      setLoading(true);
      setError("");

      const file = await getFileForApi();
      if (!file) {
        setError("No image available. Please upload an image first.");
        return;
      }

      const formData = new FormData();
      formData.append("file", file);
      formData.append("ruler_lane", "0");
      formData.append("volume_loaded", "10");
      formData.append("ruler_marks", JSON.stringify(rulerMarks));

      const response = await axios.post<AnalyzeResponse>(`${API_BASE}/analyze`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      const result = response.data;

      if (result.error) {
        setError(result.error);
        return;
      }

      setanalyze(true);
      setBands(result.bands || []);
      setSelectedBandId(null);
      setImageWidth(result.image_width || 0);
      setImageHeight(result.image_height || 0);
      if (result.annotated_image)
        setAnnotatedImageUrl(`${STATIC_BASE}${result.annotated_image}`);
      if (result.plot_url) setPlotUrl(`${STATIC_BASE}${result.plot_url}`);

    } catch (err: any) {
      console.error("analyze error:", err);
      const serverMsg =
        err?.response?.data?.error ||
        err?.response?.data?.detail ||
        err?.message ||
        "Failed to analyze image.";
      setError(`Error: ${serverMsg}`);
    } finally {
      setLoading(false);
    }
  };

  // ─── Manual band ──────────────────────────────────────────────────────────
  /**
   * Adds a manual band at the clicked canvas position by interpolating kDa and concentration
   * from the nearest ruler ladder bands using logarithmic interpolation.
   */
  const handleManualBandAdd = (clickX: number, clickY: number) => {
    const ladderBands = bands.filter((b) => b.lane === 0);
    const referenceBands = ladderBands.length >= 2 ? ladderBands : bands;

    const { molecularWeight, concentration } = interpolateBandValues(
      referenceBands,
      clickY,
      imageHeight
    );

    const newId = Date.now();
    const newBand: Band & { isManual: boolean } = {
      id: newId,
      name: `Manual-${manualBandCounter}`,
      molecularWeight,
      concentration,
      intensity: 0,
      relativeQuantity: 0,
      lane: -1,
      x: clickX,
      y: clickY,
      isManual: true,
    };

    setBands((prev) => [...prev, newBand]);
    setManualBandCounter((c) => c + 1);
    setSelectedBandId(newId);
  };

  // ─── Report ───────────────────────────────────────────────────────────────
  const handleAddToReport = (band: Band) => {
    setReportBands((prev) => {
      if (prev.some((b) => b.id === band.id)) return prev;
      return [...prev, band];
    });
    setShowReport(true);
  };

  const handleRemoveFromReport = (id: number) => {
    setReportBands((prev) => prev.filter((b) => b.id !== id));
  };

  const handleExportBoth = () => {
    const exportCsv = (rows: Band[], filename: string) => {
      const headers = ["ID", "Name", "Lane", "kDa", "Intensity", "Relative Qty", "Concentration"];
      const data = rows.map((b) => [
        b.id, b.name, b.lane, b.molecularWeight,
        b.intensity, b.relativeQuantity, b.concentration,
      ]);
      const csv = [headers, ...data]
        .map((row) => row.map((c) => `"${c}"`).join(","))
        .join("\n");
      const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      link.click();
      URL.revokeObjectURL(url);
    };

    if (bands.length)       exportCsv(bands,       "all_bands.csv");
    if (reportBands.length) setTimeout(() => exportCsv(reportBands, "report_bands.csv"), 300);
  };

  // ─── Render ───────────────────────────────────────────────────────────────
  return (
    <div className="app-shell">
      {error && <div className="error-box">{error}</div>}

      <div className="layout-grid">
        {/* LEFT COLUMN */}
        <section className="left-column">
          <UploadPanel
            selectedFile={selectedFile}
            onFileChange={handleFileChange}
            onAnalyze={handleAnalyze}
            loading={loading}
            disabledAnalyze={!canAnalyze}
            fetchAllImages={fetchAllImages}
          />

          {previewUrl && (
            <div className="panel-card card-elevated">
              <div className="panel-topbar">
                <div>
                  <h2 className="section-title">Lane 0 Range Selection</h2>
                  <p className="section-subtitle">
                    Click the top-most and bottom-most ruler bands on lane 0.
                  </p>
                </div>

                <div className="topbar-actions">
                  <button
                    className="primary-btn"
                    type="button"
                    onClick={() => {
                      setLane0MarkMode((prev) => !prev);
                      setLane0TopBottomMarks([]);
                      setRulerMarks([]);
                      setBands([]);
                      setSelectedBandId(null);
                      setanalyze(false);
                    }}
                  >
                    {lane0MarkMode ? "Stop Marking" : "Mark Lane 0"}
                  </button>

                  <button
                    className="secondary-btn"
                    type="button"
                    onClick={handleResetLane0}
                    disabled={!lane0TopBottomMarks.length && !rulerMarks.length}
                  >
                    Reset
                  </button>

                  <button
                    className="primary-btn"
                    onClick={handleAnalyze}
                    disabled={loading || !canAnalyze}
                    type="button"
                  >
                    {loading ? "Analyzing..." : "Analyze Image"}
                  </button>
                </div>
              </div>

              <RulerMarker
                imageUrl={previewUrl}
                markMode={lane0MarkMode}
                topBottomMarks={lane0TopBottomMarks}
                detectedRulerMarks={rulerMarks}
                onAddMark={handleAddLane0Mark}
              />
            </div>
          )}

          <ImageViewer
            previewUrl={previewUrl}
            annotatedImageUrl={annotatedImageUrl}
            plotUrl={plotUrl}
            bands={bands}
            selectedBandId={selectedBandId}
            onSelectBand={setSelectedBandId}
            imageWidth={imageWidth}
            imageHeight={imageHeight}
            onAddToReport={analyze ? handleAddToReport : undefined}
            manualAddMode={manualAddMode}
            onManualBandAdd={handleManualBandAdd}
          />

          {analyze && bands.length > 0 && (
            <div className="action-row">
              <button
                className={manualAddMode ? "primary-btn" : "secondary-btn"}
                type="button"
                onClick={() => setManualAddMode((v) => !v)}
              >
                {manualAddMode ? "✋ Stop Adding Bands" : "➕ Add Manual Band"}
              </button>

              {(bands.length > 0 || reportBands.length > 0) && (
                <button className="primary-btn" type="button" onClick={handleExportBoth}>
                  Export Both Tables
                </button>
              )}
            </div>
          )}
        </section>

        {/* RIGHT COLUMN */}
        <aside className="right-column">
          {!analyze ? (
            <div className="panel-card sticky-panel card-elevated">
              <h2 className="section-title">Lane 0 kDa Input</h2>

              {!previewUrl && (
                <p className="muted-text">Upload an image to begin.</p>
              )}

              {!!previewUrl && !lane0TopBottomMarks.length && !rulerMarks.length && (
                <p className="muted-text">
                  Click <strong>Mark Lane 0</strong> then select the top and bottom ruler bands.
                </p>
              )}

              {lane0TopBottomMarks.length === 1 && !rulerMarks.length && (
                <p className="muted-text">
                  Top point marked. Now click the bottom ruler band.
                </p>
              )}

              {lane0TopBottomMarks.length === 2 && !rulerMarks.length && loading && (
                <p className="muted-text">Detecting ruler bands…</p>
              )}

              {!!rulerMarks.length && (
                <div className="kda-input-list">
                  {!areRulerValuesValid() && (
                    <div className="warning-box">
                      Enter kDa values from top to bottom in strictly descending order (e.g. 180 → 130 → 100…).
                    </div>
                  )}
                  {rulerMarks.map((mark) => (
                    <div key={mark.id} className="kda-input-row">
                      <div className="kda-badge">R{mark.id}</div>
                      <div className="field-box">
                        <input
                          type="number"
                          placeholder="kDa"
                          value={mark.kda || ""}
                          onChange={(e) => handleKdaChange(mark.id, e.target.value)}
                          className="text-input"
                          min="0"
                          step="any"
                        />
                      </div>
                      <div className="field-box">
                        <input
                          type="number"
                          placeholder="Concentration"
                          value={mark.concentration || ""}
                          onChange={(e) =>
                            handleConcentrationChange(mark.id, e.target.value)
                          }
                          className="text-input"
                          min="0"
                          step="any"
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <>
              <BandTable
                bands={bands}
                selectedBandId={selectedBandId}
                onSelectBand={setSelectedBandId}
              />

              {!showReport && (
                <button
                  className="secondary-btn"
                  type="button"
                  style={{ marginTop: 12 }}
                  onClick={() => setShowReport(true)}
                  disabled={reportBands.length === 0}
                >
                  {reportBands.length > 0
                    ? `Show Report (${reportBands.length} bands)`
                    : "No bands in report yet"}
                </button>
              )}

              {showReport && (
                <ReportTable
                  bands={reportBands}
                  onRemoveBand={handleRemoveFromReport}
                  onClose={() => setShowReport(false)}
                />
              )}
            </>
          )}
        </aside>
      </div>

      {/* Image gallery popup */}
      {showPopup && (
        <div
          className="popup-overlay"
          onClick={(e) => {
            if ((e.target as HTMLElement).classList.contains("popup-overlay"))
              setShowPopup(false);
          }}
        >
          <div className="popup-box">
            <div className="popup-header">
              <h3>Uploaded Images</h3>
              <button
                className="popup-close-btn"
                type="button"
                onClick={() => setShowPopup(false)}
              >
                ✕
              </button>
            </div>

            {allImages.length === 0 ? (
              <p className="muted-text" style={{ padding: "20px" }}>
                No uploaded images found.
              </p>
            ) : (
              <div className="popup-grid">
                {allImages.map((img) => (
                  <div key={img.id} className="popup-card">
                    <img
                      src={popupThumbnails[img.id] || `${STATIC_BASE}${img.image_url}`}
                      alt=""
                      onClick={() => selectImage(img)}
                    />
                    <p>{img.image_name}</p>
                    <button
                      className="delete-btn"
                      type="button"
                      onClick={() => deleteImage(img.id)}
                    >
                      Delete
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default WesternModule;