/**
 * TEM Export Utilities
 * Supports: PDF (image + table), Excel (summary + data), PNG (annotated image)
 */

/**
 * Renders the TEM image with all particle circles onto an offscreen canvas
 * at the image's native resolution (viewScale = 1), returning a PNG data URL.
 */
export async function captureAnnotatedImage(displayImageUrl, boxes, minNm) {
  return new Promise((resolve, reject) => {
    if (!displayImageUrl) {
      reject(new Error("No image URL provided"));
      return;
    }

    const img = new Image();
    img.crossOrigin = "anonymous";

    img.onload = () => {
      const canvas = document.createElement("canvas");
      canvas.width = img.naturalWidth;
      canvas.height = img.naturalHeight;
      const ctx = canvas.getContext("2d");
      if (!ctx) {
        reject(new Error("Canvas 2D context unavailable"));
        return;
      }

      ctx.drawImage(img, 0, 0);

      const safeBoxes = Array.isArray(boxes) ? boxes : [];
      safeBoxes.forEach((b) => {
        const diameter = b.diameter_nm ?? null;
        if (minNm && diameter != null && diameter < minNm) return;

        const cx = b.cx ?? b.x;
        const cy = b.cy ?? b.y;
        const r = b.r;
        if (cx == null || cy == null || !r) return;

        ctx.strokeStyle =
          b.viability === "intact"
            ? "green"
            : b.viability === "not_intact"
            ? "red"
            : "orange";
        ctx.lineWidth = Math.max(2, r * 0.05);
        ctx.beginPath();
        ctx.arc(cx, cy, r, 0, Math.PI * 2);
        ctx.stroke();

        if (b.number != null) {
          const fontSize = Math.max(12, Math.min(28, Math.floor(r * 0.5)));
          ctx.save();
          ctx.font = `bold ${fontSize}px Arial`;
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          ctx.lineWidth = 3;
          ctx.strokeStyle = "black";
          ctx.strokeText(String(b.number), cx, cy);
          ctx.fillStyle = "white";
          ctx.fillText(String(b.number), cx, cy);
          ctx.restore();
        }
      });

      resolve(canvas.toDataURL("image/png"));
    };

    img.onerror = () => reject(new Error("Failed to load image for export"));
    img.src = displayImageUrl;
  });
}

function buildTableRows(intactData, notIntactData, needsReviewData) {
  const sortByNumber = (arr) => arr.slice().sort((a, b) => (a.number ?? 0) - (b.number ?? 0));
  const toRow = (c, statusLabel) => ({
    status: statusLabel,
    diameter: c.diameter_nm != null ? Number(c.diameter_nm).toFixed(2) : "-",
    number: c.number ?? "-",
  });

  return [
    ...sortByNumber(needsReviewData).map((c) => toRow(c, "Needs Review")),
    ...sortByNumber(notIntactData).map((c) => toRow(c, "Non-Intact")),
    ...sortByNumber(intactData).map((c) => toRow(c, "Intact")),
  ];
}

function buildSummary(intactData, notIntactData, needsReviewData) {
  const total = intactData.length + notIntactData.length + needsReviewData.length;
  const pct = (n) => (total > 0 ? ((n / total) * 100).toFixed(1) + "%" : "0%");
  return {
    total,
    intact: intactData.length,
    notIntact: notIntactData.length,
    review: needsReviewData.length,
    intactPct: pct(intactData.length),
    notIntactPct: pct(notIntactData.length),
    reviewPct: pct(needsReviewData.length),
  };
}

/** Exports a single-image PDF: annotated image on page 1, full particle table on page 2. */
export async function exportToPDF(
  imageDataUrl,
  intactData,
  notIntactData,
  needsReviewData,
  imageName
) {
  const { jsPDF } = await import("jspdf");
  const { default: autoTable } = await import("jspdf-autotable");

  const summary = buildSummary(intactData, notIntactData, needsReviewData);
  const rows = buildTableRows(intactData, notIntactData, needsReviewData);

  const doc = new jsPDF({ orientation: "landscape", unit: "mm", format: "a4" });
  const pageW = doc.internal.pageSize.getWidth();
  const pageH = doc.internal.pageSize.getHeight();

  // ── Page 1: header + image + summary ──
  doc.setFontSize(16);
  doc.setFont("helvetica", "bold");
  doc.text(`TEM Analysis Report`, 14, 14);

  doc.setFontSize(10);
  doc.setFont("helvetica", "normal");
  doc.text(`Image: ${imageName}`, 14, 21);

  // Summary pills row
  const pillY = 27;
  const pills = [
    { label: "Total", value: summary.total, color: [80, 80, 80] },
    { label: "Intact", value: `${summary.intact} (${summary.intactPct})`, color: [39, 174, 96] },
    { label: "Non-Intact", value: `${summary.notIntact} (${summary.notIntactPct})`, color: [192, 57, 43] },
    { label: "Needs Review", value: `${summary.review} (${summary.reviewPct})`, color: [211, 84, 0] },
  ];
  let pillX = 14;
  pills.forEach(({ label, value, color }) => {
    doc.setFillColor(...color);
    doc.setTextColor(255, 255, 255);
    doc.setFontSize(8);
    const text = `${label}: ${value}`;
    const w = doc.getTextWidth(text) + 6;
    doc.roundedRect(pillX, pillY - 4, w, 6, 1, 1, "F");
    doc.text(text, pillX + 3, pillY);
    pillX += w + 3;
  });
  doc.setTextColor(0, 0, 0);

  // Image block
  const imgY = 36;
  const maxImgH = pageH - imgY - 10;
  const maxImgW = pageW - 28;

  try {
    const imgProps = doc.getImageProperties(imageDataUrl);
    const ratio = Math.min(maxImgW / imgProps.width, maxImgH / imgProps.height);
    const imgW = imgProps.width * ratio;
    const imgH = imgProps.height * ratio;
    const imgX = 14 + (maxImgW - imgW) / 2;
    doc.addImage(imageDataUrl, "PNG", imgX, imgY, imgW, imgH);
  } catch {
    doc.setFontSize(9);
    doc.text("(Image not available)", 14, imgY + 10);
  }

  // ── Page 2: particle table ──
  doc.addPage();
  doc.setFontSize(13);
  doc.setFont("helvetica", "bold");
  doc.text("Particle Analysis Table", 14, 14);

  const statusColor = (status) => {
    if (status === "Intact") return [39, 174, 96];
    if (status === "Non-Intact") return [192, 57, 43];
    return [211, 84, 0];
  };

  autoTable(doc, {
    startY: 20,
    head: [["Status", "Diameter (nm)", "Particle #"]],
    body: rows.map((r) => [r.status, r.diameter, r.number]),
    styles: { fontSize: 8, cellPadding: 2 },
    headStyles: { fillColor: [41, 128, 185], textColor: 255, fontStyle: "bold" },
    alternateRowStyles: { fillColor: [245, 245, 245] },
    didDrawCell: (data) => {
      if (data.section === "body" && data.column.index === 0) {
        const status = rows[data.row.index]?.status;
        if (status) {
          const [r, g, b] = statusColor(status);
          doc.setFillColor(r, g, b);
          doc.setTextColor(255, 255, 255);
          doc.roundedRect(
            data.cell.x + 1,
            data.cell.y + 1,
            data.cell.width - 2,
            data.cell.height - 2,
            1,
            1,
            "F"
          );
          doc.setFontSize(7);
          doc.text(
            status,
            data.cell.x + data.cell.width / 2,
            data.cell.y + data.cell.height / 2,
            { align: "center", baseline: "middle" }
          );
        }
      }
    },
  });

  doc.save(`${imageName}_TEM_report.pdf`);
}

/** Exports an Excel workbook: Summary sheet + full Particles sheet. */
export async function exportToExcel(
  intactData,
  notIntactData,
  needsReviewData,
  imageName
) {
  const XLSX = await import("xlsx");

  const summary = buildSummary(intactData, notIntactData, needsReviewData);
  const rows = buildTableRows(intactData, notIntactData, needsReviewData);

  const wb = XLSX.utils.book_new();

  // Summary sheet
  const summaryAoa = [
    ["TEM Analysis Report"],
    ["Image", imageName],
    [],
    ["Metric", "Count", "Percentage"],
    ["Total Particles", summary.total, "100%"],
    ["Intact", summary.intact, summary.intactPct],
    ["Non-Intact", summary.notIntact, summary.notIntactPct],
    ["Needs Review", summary.review, summary.reviewPct],
  ];
  const summarySheet = XLSX.utils.aoa_to_sheet(summaryAoa);
  summarySheet["!cols"] = [{ wch: 20 }, { wch: 12 }, { wch: 14 }];
  XLSX.utils.book_append_sheet(wb, summarySheet, "Summary");

  // Particles sheet
  const particleAoa = [
    ["Status", "Diameter (nm)", "Particle #"],
    ...rows.map((r) => [r.status, r.diameter === "-" ? "" : parseFloat(r.diameter), r.number]),
  ];
  const particleSheet = XLSX.utils.aoa_to_sheet(particleAoa);
  particleSheet["!cols"] = [{ wch: 16 }, { wch: 16 }, { wch: 12 }];
  XLSX.utils.book_append_sheet(wb, particleSheet, "Particles");

  XLSX.writeFile(wb, `${imageName}_TEM_analysis.xlsx`);
}

/** Triggers a PNG download of the annotated image data URL. */
export function exportToPNG(imageDataUrl, imageName) {
  const a = document.createElement("a");
  a.href = imageDataUrl;
  a.download = `${imageName}_TEM_annotated.png`;
  a.click();
}

/**
 * Batch export: given an array of { imageDataUrl, intactData, notIntactData,
 * needsReviewData, imageName } objects, exports a single multi-page PDF.
 */
export async function exportBatchToPDF(items) {
  if (!items.length) return;

  const { jsPDF } = await import("jspdf");
  const { default: autoTable } = await import("jspdf-autotable");

  const doc = new jsPDF({ orientation: "landscape", unit: "mm", format: "a4" });
  const pageW = doc.internal.pageSize.getWidth();
  const pageH = doc.internal.pageSize.getHeight();

  items.forEach(({ imageDataUrl, intactData, notIntactData, needsReviewData, imageName }, idx) => {
    if (idx > 0) doc.addPage();

    const summary = buildSummary(intactData, notIntactData, needsReviewData);
    const rows = buildTableRows(intactData, notIntactData, needsReviewData);

    doc.setFontSize(13);
    doc.setFont("helvetica", "bold");
    doc.text(`${imageName}`, 14, 14);
    doc.setFontSize(9);
    doc.setFont("helvetica", "normal");
    doc.text(
      `Total: ${summary.total}  |  Intact: ${summary.intact} (${summary.intactPct})  |  Non-Intact: ${summary.notIntact} (${summary.notIntactPct})  |  Review: ${summary.review} (${summary.reviewPct})`,
      14,
      21
    );

    const imgY = 26;
    const maxImgH = pageH - imgY - 10;
    const maxImgW = (pageW - 28) * 0.6;

    try {
      const imgProps = doc.getImageProperties(imageDataUrl);
      const ratio = Math.min(maxImgW / imgProps.width, maxImgH / imgProps.height);
      doc.addImage(imageDataUrl, "PNG", 14, imgY, imgProps.width * ratio, imgProps.height * ratio);
    } catch {/* skip image if unavailable */}

    // Compact table on the right side of the page
    autoTable(doc, {
      startY: imgY,
      margin: { left: pageW * 0.63 },
      head: [["Status", "Diameter (nm)", "#"]],
      body: rows.map((r) => [r.status, r.diameter, r.number]),
      styles: { fontSize: 7, cellPadding: 1.5 },
      headStyles: { fillColor: [41, 128, 185], textColor: 255 },
      alternateRowStyles: { fillColor: [245, 245, 245] },
    });
  });

  doc.save(`TEM_batch_report.pdf`);
}
