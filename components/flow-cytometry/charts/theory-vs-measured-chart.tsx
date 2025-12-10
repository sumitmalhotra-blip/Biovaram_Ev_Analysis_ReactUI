"use client"

import {
  ComposedChart,
  Line,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts"

// Generate Mie theory curve and measured data
const generateData = () => {
  const data = []

  for (let diameter = 20; diameter <= 500; diameter += 10) {
    // Simplified Mie scattering intensity (theoretical)
    const theory = Math.pow(diameter / 100, 4) * 1000 * Math.exp(-diameter / 300)
    // Measured with some noise
    const measured = theory * (0.85 + Math.random() * 0.3)

    data.push({
      diameter,
      theory: Math.round(theory),
      measured: Math.round(measured),
    })
  }

  return data
}

const data = generateData()

export function TheoryVsMeasuredChart() {
  return (
    <div className="h-80">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis
            dataKey="diameter"
            stroke="#64748b"
            tick={{ fontSize: 11 }}
            label={{ value: "Diameter (nm)", position: "bottom", offset: -5, fill: "#64748b", fontSize: 12 }}
          />
          <YAxis
            stroke="#64748b"
            tick={{ fontSize: 11 }}
            label={{
              value: "Scattering Intensity (a.u.)",
              angle: -90,
              position: "insideLeft",
              fill: "#64748b",
              fontSize: 12,
            }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "#1e293b",
              border: "1px solid #334155",
              borderRadius: "8px",
              fontSize: "12px",
            }}
            labelFormatter={(value) => `${value} nm`}
          />
          <Legend wrapperStyle={{ fontSize: "12px" }} />
          <Line type="monotone" dataKey="theory" stroke="#8b5cf6" strokeWidth={2} dot={false} name="Mie Theory" />
          <Scatter dataKey="measured" fill="#3b82f6" fillOpacity={0.7} name="Measured Data" />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
