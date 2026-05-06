import { useState } from "react";
import axios from "axios";
import "../../App.css";
import type { Band } from "./BandTable";

import { WESTERN_API as API_BASE, STATIC_BASE } from "../../services/api";

type ReportSummary = {
  total_bands: number;
  lanes_covered: number[];
  kda_range: { min: number; max: number };
  intensity: { mean: number; min: number; max: number };
  relative_quantity: { mean: number; total: number };
  concentration: { mean: number; total: number };
};

type Props = {
  bands: Band[];
  onRemoveBand: (id: number) => void;
  onClose: () => void;
};

function ReportTable({ bands, onRemoveBand, onClose }: Props) {
  const [summary, setSummary] = useState<ReportSummary | null>(null);
  const [reportCsvUrl, setReportCsvUrl] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleGenerateReport = async () => {
    if (!bands.length) return;

    try {
      setLoading(true);
      setError("");

      const payload = {
        bands: bands.map((b) => ({
          id: b.id,
          name: b.name,
          lane: b.lane,
          x: b.x,
          y: b.y,
          molecularWeight: parseFloat(String(b.molecularWeight)),
          intensity: b.intensity,
          relativeQuantity: b.relativeQuantity,
          concentration: parseFloat(String(b.concentration)),
        })),
      };

      const res = await axios.post(`${API_BASE}/report/band-report`, payload);
      const data = res.data;

      setSummary(data.summary);
      setReportCsvUrl(`${STATIC_BASE}${data.report_csv}`);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to generate report.");
    } finally {
      setLoading(false);
    }
  };

  const handleExportCSV = () => {
    if (reportCsvUrl) {
      // Download the server-generated CSV
      const link = document.createElement("a");
      link.href = reportCsvUrl;
      link.download = "band_report.csv";
      link.click();
      return;
    }

    // Fallback: build CSV client-side if API hasn't been called yet
    if (!bands.length) return;
    const headers = ["ID", "Name", "Lane", "kDa", "Intensity", "Relative Qty", "Concentration"];
    const rows = bands.map((b) => [
      b.id, b.name, b.lane, b.molecularWeight, b.intensity, b.relativeQuantity, b.concentration,
    ]);
    const csv = [headers, ...rows]
      .map((row) => row.map((c) => `"${c}"`).join(","))
      .join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "band_report.csv";
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="panel-card report-table-panel">
      <div className="panel-topbar">
        <div>
          <h2 className="section-title">Band Report</h2>
          <p className="section-subtitle">
            {bands.length} band{bands.length !== 1 ? "s" : ""} selected
          </p>
        </div>
        <div className="topbar-report">
          <button
            className="primary-btn"
            type="button"
            onClick={handleGenerateReport}
            disabled={!bands.length || loading}
          >
            {loading ? "Generating..." : "Generate Report"}
          </button>
          <button
            className="secondary-btn"
            type="button"
            onClick={handleExportCSV}
            disabled={!bands.length}
          >
            Export CSV
          </button>
          <button className="secondary-btn" type="button" onClick={onClose}>
            Close
          </button>
        </div>
      </div>

      {error && <div className="error-box" style={{ marginBottom: 10 }}>{error}</div>}

      {/* Summary stats from API */}
      {summary && (
        <div className="report-summary-grid">
          <div className="report-summary-card">
            <span className="summary-label">Total Bands</span>
            <span className="summary-value">{summary.total_bands}</span>
          </div>
          <div className="report-summary-card">
            <span className="summary-label">Lanes</span>
            <span className="summary-value">{summary.lanes_covered.join(", ")}</span>
          </div>
          <div className="report-summary-card">
            <span className="summary-label">kDa Range</span>
            <span className="summary-value">{summary.kda_range.min} – {summary.kda_range.max}</span>
          </div>
          <div className="report-summary-card">
            <span className="summary-label">Avg Intensity</span>
            <span className="summary-value">{summary.intensity.mean}</span>
          </div>
          <div className="report-summary-card">
            <span className="summary-label">Total Rel. Qty</span>
            <span className="summary-value">{summary.relative_quantity.total}</span>
          </div>
          <div className="report-summary-card">
            <span className="summary-label">Total Concentration</span>
            <span className="summary-value">{summary.concentration.total}</span>
          </div>
        </div>
      )}

      {!bands.length ? (
        <p className="muted-text" style={{ padding: "16px 0" }}>
          No bands added yet. Right-click a band dot on the image to add it here.
        </p>
      ) : (
        <div className="table-wrap">
          <table className="band-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Lane</th>
                <th>kDa</th>
                <th>Intensity</th>
                <th>Relative Qty</th>
                <th>Concentration</th>
                <th>Remove</th>
              </tr>
            </thead>
            <tbody>
              {bands.map((band) => (
                <tr key={band.id}>
                  <td>{band.id}</td>
                  <td>{band.name}</td>
                  <td>{band.lane}</td>
                  <td>{band.molecularWeight}</td>
                  <td>{band.intensity}</td>
                  <td>{band.relativeQuantity}</td>
                  <td>{band.concentration}</td>
                  <td>
                    <button
                      type="button"
                      className="delete-btn"
                      onClick={() => onRemoveBand(band.id)}
                      title="Remove from report"
                    >
                      ✕
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default ReportTable;