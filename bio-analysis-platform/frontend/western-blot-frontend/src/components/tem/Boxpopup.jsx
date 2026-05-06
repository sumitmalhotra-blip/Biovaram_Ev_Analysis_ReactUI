import { useEffect, useState } from "react";

function BoxPopup({ box, onClose, onSave, onChange }) {
  const [data, setData] = useState(box);

  useEffect(() => setData(box), [box]);

  const update = (patch) => {
    const next = { ...data, ...patch };
    setData(next);
    onChange?.(next);
  };

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.45)",
        backdropFilter: "blur(3px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 9999,
        padding: 16,
      }}
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        style={{
          width: 380,
          maxWidth: "100%",
          background: "#fff",
          borderRadius: 16,
          boxShadow: "0 16px 45px rgba(0,0,0,0.28)",
          overflow: "hidden",
          border: "1px solid #e5e7eb",
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: "14px 16px",
            borderBottom: "1px solid #eef2f7",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div style={{ fontSize: 16, fontWeight: 900, color: "#111827" }}>
            Edit Circle
          </div>
          <button
            onClick={onClose}
            style={{
              border: "1px solid #e5e7eb",
              background: "#fff",
              width: 34,
              height: 34,
              borderRadius: 10,
              cursor: "pointer",
              lineHeight: 1,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontWeight: 900,
            }}
            aria-label="Close"
            title="Close"
          >
            ✕
          </button>
        </div>

        {/* Body */}
        <div style={{ padding: 16 }}>
          <div style={{ display: "grid", gap: 12 }}>
            {/* Viability */}
            <div>
              <div style={{ fontSize: 12, fontWeight: 800, color: "#374151", marginBottom: 6 }}>
                Viability
              </div>
              <select
                value={data.viability ?? "needs_review"}
                onChange={(e) => update({ viability: e.target.value })}
                style={{
                  width: "100%",
                  padding: "10px 12px",
                  borderRadius: 12,
                  border: "1px solid #e5e7eb",
                  outline: "none",
                  fontSize: 14,
                  background: "#fff",
                }}
              >
                <option value="intact">Intact</option>
                <option value="not_intact">Not Intact</option>
                <option value="needs_review">Needs Review</option>
              </select>
            </div>

            {/* Diameter */}
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                <div style={{ fontSize: 12, fontWeight: 800, color: "#374151", marginBottom: 6 }}>
                  Diameter (nm)
                </div>
                <div style={{ fontSize: 11, color: "#6b7280" }}>
                  (Updates circle instantly)
                </div>
              </div>

              <input
                type="number"
                min="0"
                step="0.1"
                value={data.diameter_nm ?? ""}
                onChange={(e) => {
                  const v = e.target.value;
                  const d = v === "" ? null : Number(v);
                  update({ diameter_nm: d });
                }}
                style={{
                  width: "100%",
                  padding: "10px 12px",
                  borderRadius: 12,
                  border: "1px solid #e5e7eb",
                  outline: "none",
                  fontSize: 14,
                }}
              />

              <input
                type="range"
                min="0"
                max="500"
                value={data.diameter_nm ?? 0}
                onChange={(e) => update({ diameter_nm: Number(e.target.value) })}
                style={{ width: "100%", marginTop: 10 }}
              />
            </div>
          </div>
        </div>

        {/* Footer buttons */}
        <div
          style={{
            padding: 16,
            borderTop: "1px solid #eef2f7",
            display: "flex",
            justifyContent: "space-between",
            gap: 10,
          }}
        >
          {/* Delete */}
          <button
            onClick={() => {
              if (window.confirm("Delete this circle?")) onSave(null);
            }}
            style={{
              background: "#ff4d4f",
              color: "#fff",
              border: "none",
              padding: "10px 14px",
              borderRadius: 12,
              cursor: "pointer",
              fontWeight: 900,
              boxShadow: "0 10px 18px rgba(220,38,38,0.18)",
            }}
          >
            Delete
          </button>

          <div style={{ display: "flex", gap: 10 }}>
            <button
              onClick={onClose}
              style={{
                background: "#fff",
                color: "#111827",
                border: "1px solid #e5e7eb",
                padding: "10px 14px",
                borderRadius: 12,
                cursor: "pointer",
                fontWeight: 800,
              }}
            >
              Cancel
            </button>

            <button
              onClick={() => onSave(data)}
              style={{
                background: "#1976d2",
                color: "#fff",
                border: "none",
                padding: "10px 16px",
                borderRadius: 12,
                cursor: "pointer",
                fontWeight: 900,
                boxShadow: "0 10px 20px rgba(25,118,210,0.25)",
              }}
            >
              Save
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default BoxPopup;
