import { useState } from "react";

function BoxPopup({ box, onClose, onSave }) {
  const [data, setData] = useState(box);

  return (
    <div style={{
      position: "fixed",
      inset: 0,
      background: "rgba(0,0,0,0.4)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      zIndex: 999
    }}>
      <div style={{ background: "#fff", padding: 20, width: 300 }}>
        <h3>Edit Circle</h3>

        <label>Viability</label>
        <select
          value={data.viability}
          onChange={e => setData({ ...data, viability: e.target.value })}
        >
          <option value="viable">Viable</option>
          <option value="non_viable">Non-Viable</option>
          <option value="review">Review</option>
        </select>

        <br /><br />

        <label>Diameter (nm)</label>
        <input
          type="number"
          value={data.diameter_nm}
          onChange={e => {
            const d = +e.target.value;
            setData({ ...data, diameter_nm: d, r: d / 2 });
          }}
        />

        <br /><br />

        <div style={{ textAlign: "right" }}>
          <button onClick={onClose}>Cancel</button>
          <button onClick={() => onSave(data)} style={{ marginLeft: 10 }}>
            Save
          </button>
        </div>
      </div>
    </div>
  );
}

export default BoxPopup;
