import { useEffect, useRef, useState } from "react";
import { clamp } from "./canvasUtils";

// ✅ Intensity Panel Component (same behavior)
export default function IntensityPanel({ result, onClose, onHoverPoint }) {
  const [pos, setPos] = useState({ x: 0, y: 0 });
  const [dragging, setDragging] = useState(false);
  const [hoverIdx, setHoverIdx] = useState(null);

  const dragRef = useRef({ startX: 0, startY: 0, baseX: 0, baseY: 0 });
  const svgRef = useRef(null);

  // table auto-scroll helpers
  const rowRefs = useRef([]);

  // avoid table jumping
  const lastHoverSourceRef = useRef("chart"); // "chart" | "table"
  const userScrollingRef = useRef(false);
  const scrollTimerRef = useRef(null);

  // hover stability
  const rafRef = useRef(null);
  const lastIdxRef = useRef(null);
  const leaveTimerRef = useRef(null);

  useEffect(() => {
    if (!dragging) return;

    const onMove = (e) => {
      const dx = e.clientX - dragRef.current.startX;
      const dy = e.clientY - dragRef.current.startY;

      setPos({
        x: dragRef.current.baseX + dx,
        y: dragRef.current.baseY + dy,
      });
    };

    const onUp = () => setDragging(false);

    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);

    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, [dragging]);

  useEffect(() => {
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      if (leaveTimerRef.current) clearTimeout(leaveTimerRef.current);
      if (scrollTimerRef.current) clearTimeout(scrollTimerRef.current);
      if (typeof onHoverPoint === "function") onHoverPoint(null);
    };
  }, [onHoverPoint]);

  useEffect(() => {
    if (hoverIdx == null) return;
    if (userScrollingRef.current) return;
    if (lastHoverSourceRef.current !== "chart") return;

    const rowEl = rowRefs.current?.[hoverIdx];
    if (!rowEl) return;

    rowEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [hoverIdx]);

  if (!result?.points?.length) return null;

  const points = result.points;
  const vals = points.map((p) => p.intensity);

  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const avg =
    result.average_intensity ??
    vals.reduce((a, b) => a + b, 0) / vals.length;

  const W = 260,
    H = 80,
    pad = 8;
  const xStep = (W - pad * 2) / (vals.length - 1 || 1);

  const normY = (v) => {
    if (max === min) return H / 2;
    const t = (v - min) / (max - min);
    return pad + (1 - t) * (H - pad * 2);
  };

  const d = vals
    .map((v, i) => `${i === 0 ? "M" : "L"} ${pad + i * xStep} ${normY(v)}`)
    .join(" ");

  const copyJSON = async () => {
    try {
      await navigator.clipboard.writeText(JSON.stringify(result, null, 2));
      alert("Copied intensity JSON ✅");
    } catch {
      alert("Copy failed");
    }
  };

  const downloadCSV = () => {
    const header = "step,x,y,intensity\n";
    const rows = points
      .map((p) => `${p.step},${p.x},${p.y},${p.intensity}`)
      .join("\n");
    const blob = new Blob([header + rows], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `line_intensity_${result.image_id}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const onMouseDownHeader = (e) => {
    if (e.button !== 0) return;

    setDragging(true);
    dragRef.current = {
      startX: e.clientX,
      startY: e.clientY,
      baseX: pos.x,
      baseY: pos.y,
    };
  };

  const avgY = normY(avg);
  const minY = normY(min);
  const maxY = normY(max);

  const setHoverByIndex = (idx, source = "chart") => {
    lastHoverSourceRef.current = source;

    if (idx == null) {
      lastIdxRef.current = null;
      setHoverIdx(null);
      if (typeof onHoverPoint === "function") onHoverPoint(null);
      return;
    }

    const safe = clamp(idx, 0, points.length - 1);
    if (lastIdxRef.current === safe) return;
    lastIdxRef.current = safe;

    setHoverIdx(safe);
    if (typeof onHoverPoint === "function") onHoverPoint(points[safe]);
  };

  const onTableScroll = () => {
    userScrollingRef.current = true;
    if (scrollTimerRef.current) clearTimeout(scrollTimerRef.current);
    scrollTimerRef.current = setTimeout(() => {
      userScrollingRef.current = false;
    }, 250);
  };

  const handlePointerMove = (e) => {
    if (leaveTimerRef.current) clearTimeout(leaveTimerRef.current);

    const svg = svgRef.current;
    if (!svg) return;

    const rect = svg.getBoundingClientRect();
    let x = e.clientX - rect.left;

    x = clamp(x, pad, W - pad);
    const idx = Math.round((x - pad) / xStep);

    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    rafRef.current = requestAnimationFrame(() => {
      setHoverByIndex(idx, "chart");
    });
  };

  const handlePointerLeave = () => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    leaveTimerRef.current = setTimeout(() => {
      if (lastHoverSourceRef.current === "chart") {
        setHoverByIndex(null, "chart");
      }
    }, 60);
  };

  const hoveredPoint = hoverIdx != null ? points[hoverIdx] : null;
  const hoverX = hoverIdx != null ? pad + hoverIdx * xStep : null;
  const hoverY = hoverIdx != null ? normY(vals[hoverIdx]) : null;

  return (
    <div
      className="intensityPanel"
      style={{ transform: `translate(${pos.x}px, ${pos.y}px)` }}
    >
      <div className="intensityHeader dragHeader" onMouseDown={onMouseDownHeader}>
        <div>
          <div className="intensityTitle">Line Intensity</div>
          <div className="intensityStats">
            Avg: {Number(avg).toFixed(1)} | Min: {min} | Max: {max}
          </div>

          <div className="intensityStats" style={{ opacity: 0.9 }}>
            Hover → Step: {hoveredPoint ? hoveredPoint.step : "—"} | I:{" "}
            {hoveredPoint ? hoveredPoint.intensity : "—"}
          </div>
        </div>

        <button className="intensityClose" onClick={onClose}>
          ✕
        </button>
      </div>

      <svg
        ref={svgRef}
        width={W}
        height={H}
        className="intensityChart"
        style={{ touchAction: "none", userSelect: "none" }}
      >
        <line
          x1={pad}
          y1={maxY}
          x2={W - pad}
          y2={maxY}
          stroke="rgba(255,80,80,0.8)"
          strokeWidth="1.5"
          strokeDasharray="4 4"
          pointerEvents="none"
        />
        <text
          x={W - pad}
          y={Math.max(pad + 10, maxY - 4)}
          textAnchor="end"
          fill="rgba(255,80,80,0.9)"
          fontSize="10"
          fontWeight="700"
          pointerEvents="none"
        >
          MAX {max}
        </text>

        <line
          x1={pad}
          y1={avgY}
          x2={W - pad}
          y2={avgY}
          stroke="rgba(255,255,255,0.6)"
          strokeWidth="1.5"
          strokeDasharray="6 4"
          pointerEvents="none"
        />
        <text
          x={W - pad}
          y={Math.max(pad + 10, avgY - 4)}
          textAnchor="end"
          fill="rgba(255,255,255,0.9)"
          fontSize="10"
          fontWeight="700"
          pointerEvents="none"
        >
          AVG {Number(avg).toFixed(1)}
        </text>

        <line
          x1={pad}
          y1={minY}
          x2={W - pad}
          y2={minY}
          stroke="rgba(80,150,255,0.8)"
          strokeWidth="1.5"
          strokeDasharray="4 4"
          pointerEvents="none"
        />
        <text
          x={W - pad}
          y={Math.max(pad + 10, minY - 4)}
          textAnchor="end"
          fill="rgba(80,150,255,0.9)"
          fontSize="10"
          fontWeight="700"
          pointerEvents="none"
        >
          MIN {min}
        </text>

        <path d={d} fill="none" stroke="white" strokeWidth="2" pointerEvents="none" />

        {hoverIdx != null && (
          <>
            <line
              x1={hoverX}
              y1={pad}
              x2={hoverX}
              y2={H - pad}
              stroke="rgba(255,255,255,0.35)"
              strokeWidth="1"
              pointerEvents="none"
            />
            <circle
              cx={hoverX}
              cy={hoverY}
              r="4"
              fill="rgba(255,255,255,0.95)"
              pointerEvents="none"
            />
            <circle
              cx={hoverX}
              cy={hoverY}
              r="7"
              fill="none"
              stroke="rgba(255,255,255,0.4)"
              strokeWidth="1"
              pointerEvents="none"
            />
          </>
        )}

        <rect
          x="0"
          y="0"
          width={W}
          height={H}
          fill="transparent"
          pointerEvents="all"
          onPointerMove={handlePointerMove}
          onPointerEnter={handlePointerMove}
          onPointerLeave={handlePointerLeave}
        />
      </svg>

      <div className="intensityBtns">
        <button onClick={copyJSON}>Copy JSON</button>
        <button onClick={downloadCSV}>Download CSV</button>
      </div>

      <div className="intensityTableWrap" onScroll={onTableScroll}>
        <table className="intensityTable">
          <thead>
            <tr>
              <th>Step</th>
              <th>Intensity</th>
            </tr>
          </thead>
          <tbody>
            {points.map((p, i) => (
              <tr
                key={p.step}
                ref={(el) => (rowRefs.current[i] = el)}
                onMouseEnter={() => setHoverByIndex(i, "table")}
                style={hoverIdx === i ? { background: "rgba(255,255,255,0.10)" } : undefined}
              >
                <td>{p.step}</td>
                <td>{p.intensity}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}