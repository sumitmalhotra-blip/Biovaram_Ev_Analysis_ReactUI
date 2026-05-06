import React from "react";
import { getImageName } from "./canvasUtils";

export default function ParticleTableView({
  showTable,
  setShowTable,
  imageUrl,
  minNm,
  viabilityMap,
  sizeFilter,
  setSizeFilter,
  fetchTable,

  tableLoading,
  tableError,

  intactData,
  notIntactData,
  needsReviewData,

  pageReview,
  setPageReview,
  pageIntact,
  setPageIntact,
  
  pageNotIntact,
  setPageNotIntact,

  showIntact,
  setShowIntact,
  showNotIntact,
  setShowNotIntact,

  focusParticleByNumber,
  setIsRightBarOpen,
}) {
  const PAGE_SIZE = 10;

  const paginate = (rows, page) => {
    const arr = Array.isArray(rows) ? rows : [];
    const total = arr.length;
    const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
    const safePage = Math.min(Math.max(1, page), totalPages);
    const start = (safePage - 1) * PAGE_SIZE;
    const end = start + PAGE_SIZE;
    return {
      total,
      totalPages,
      safePage,
      start,
      end,
      pageRows: arr.slice(start, end),
    };
  };

  const SimpleTable = ({ data }) => (
    <div className="tableWrap">
      <table className="tbl">
        <thead>
          <tr>
            <th>Particle</th>
            <th>Diameter (nm)</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {(Array.isArray(data) ? data : []).map((c) => (
            <tr key={c.number}>
              <td>
                <button className="linkBtn" onClick={() => focusParticleByNumber(c.number)}>
                  {c.number}
                </button>
              </td>
              <td>{c.diameter_nm}</td>
              <td>
                <span
                  className=""
                  style={{
                    background: viabilityMap[c.viability]?.bg,
                    color: viabilityMap[c.viability]?.color,
                    fontSize:"smaller", 
                  }}
                >
                  {viabilityMap[c.viability]?.label}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  const Pager = ({ total, start, end, safePage, totalPages, onPrev, onNext }) => (
    <div className="pager">
      <div>
        Showing <b>{total === 0 ? 0 : start + 1}</b>-<b>{Math.min(end, total)}</b> of <b>{total}</b>
      </div>
      <div className="pagerRight">
        <button className="pagerBtn" onClick={onPrev} disabled={safePage === 1}>
          Prev
        </button>
        <div>
          Page <b>{safePage}</b> / <b>{totalPages}</b>
        </div>
        <button className="pagerBtn" onClick={onNext} disabled={safePage === totalPages}>
          Next
        </button>
      </div>
    </div>
  );

  return (
    <div className="tableCard">
      <div className="tableHeader">
        <div>
          <div className="tableTitle">{getImageName(imageUrl)} - Particle Tables</div>
          <div className="tableSub">
            Hidden below <b>{minNm} nm</b> (applies to all 3 tables)
          </div>
        </div>

        <div className="tableHeaderRight">
          <select
            className="select"
            value={sizeFilter || ""}
            onChange={(e) => {
              const val = e.target.value || null;
              setSizeFilter(val);
              fetchTable(val);
            }}
          >
            <option value="">All Sizes</option>
            <option value="30_50">30–50 nm</option>
            <option value="50_100">50–100 nm</option>
            <option value="100_200">100–200 nm</option>
            <option value="200_plus">200+ nm</option>
          </select>

          <button className="refreshBtn" onClick={() => { setShowTable(false); setIsRightBarOpen(true); }}>
  Back
</button>
        </div>
      </div>

      {tableLoading && <div className="tableMsg">Loading...</div>}
      {tableError && <div className="tableErr">{tableError}</div>}

      {!tableLoading && !tableError && (
        <>
          {(() => {
            const p = paginate(needsReviewData, pageReview);
            return (
              <div className="section section--review">
                <div className="sectionRow">
                  <div className="sectionTitle">Needs Review ({p.total})</div>
                </div>
                <SimpleTable data={p.pageRows} />
                <Pager
                  total={p.total}
                  start={p.start}
                  end={p.end}
                  safePage={p.safePage}
                  totalPages={p.totalPages}
                  onPrev={() => setPageReview((x) => Math.max(1, x - 1))}
                  onNext={() => setPageReview((x) => Math.min(p.totalPages, x + 1))}
                />
              </div>
            );
          })()}

          {(() => {
            const p = paginate(intactData, pageIntact);
            return (
              <div className="section section--intact">
                <div className="sectionRow">
                  <div className="sectionTitle">Intact ({p.total})</div>
                  <button className="expandBtn" onClick={() => setShowIntact((v) => !v)}>
                    {showIntact ? "Collapse" : "Expand"}
                  </button>
                </div>

                {showIntact && (
                  <>
                    <SimpleTable data={p.pageRows} />
                    <Pager
                      total={p.total}
                      start={p.start}
                      end={p.end}
                      safePage={p.safePage}
                      totalPages={p.totalPages}
                      onPrev={() => setPageIntact((x) => Math.max(1, x - 1))}
                      onNext={() => setPageIntact((x) => Math.min(p.totalPages, x + 1))}
                    />
                  </>
                )}
              </div>
            );
          })()}

          {(() => {
            const p = paginate(notIntactData, pageNotIntact);
            return (
              <div className="section section--notintact">
                <div className="sectionRow">
                  <div className="sectionTitle">Non Intact ({p.total})</div>
                  <button className="expandBtn" onClick={() => setShowNotIntact((v) => !v)}>
                    {showNotIntact ? "Collapse" : "Expand"}
                  </button>
                </div>

                {showNotIntact && (
                  <>
                    <SimpleTable data={p.pageRows} />
                    <Pager
                      total={p.total}
                      start={p.start}
                      end={p.end}
                      safePage={p.safePage}
                      totalPages={p.totalPages}
                      onPrev={() => setPageNotIntact((x) => Math.max(1, x - 1))}
                      onNext={() => setPageNotIntact((x) => Math.min(p.totalPages, x + 1))}
                    />
                  </>
                )}
              </div>
            );
          })()}
        </>
      )}
    </div>
  );
}