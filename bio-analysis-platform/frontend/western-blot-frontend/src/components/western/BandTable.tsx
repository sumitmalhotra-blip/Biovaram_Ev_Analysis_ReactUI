import { useEffect, useMemo, useState } from "react";
import "../../App.css";

export type Band = {
  id: number;
  name: string;
  molecularWeight: string;
  concentration: string;
  intensity: number;
  relativeQuantity: number;
  lane: number;
  x: number;
  y: number;
};

type Props = {
  bands: Band[];
  selectedBandId: number | null;
  onSelectBand: (id: number) => void;
};

function BandTable({ bands, selectedBandId, onSelectBand }: Props) {
  const [currentPage, setCurrentPage] = useState(1);
  const rowsPerPage = 10;

  useEffect(() => {
    setCurrentPage(1);
  }, [bands]);

  useEffect(() => {
    if (!selectedBandId) return;

    const selectedIndex = bands.findIndex((band) => band.id === selectedBandId);
    if (selectedIndex === -1) return;

    const selectedPage = Math.floor(selectedIndex / rowsPerPage) + 1;
    setCurrentPage(selectedPage);
  }, [selectedBandId, bands]);

  const totalPages = Math.ceil(bands.length / rowsPerPage);

  const paginatedBands = useMemo(() => {
    const startIndex = (currentPage - 1) * rowsPerPage;
    const endIndex = startIndex + rowsPerPage;
    return bands.slice(startIndex, endIndex);
  }, [bands, currentPage]);

  const handlePrevious = () => {
    setCurrentPage((prev) => Math.max(prev - 1, 1));
  };

  const handleNext = () => {
    setCurrentPage((prev) => Math.min(prev + 1, totalPages));
  };

  return (
    <div className="card card-elevated">
      <h2 className="section-title">Detected Bands</h2>

      {!bands.length ? (
        <p className="muted-text">No band data yet.</p>
      ) : (
        <>
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
                </tr>
              </thead>
              <tbody>
                {paginatedBands.map((band) => (
                  <tr
                    key={band.id}
                    onClick={() => onSelectBand(band.id)}
                    className={selectedBandId === band.id ? "selected-row" : ""}
                    style={{ cursor: "pointer" }}
                  >
                    <td>{band.id}</td>
                    <td>{band.name}</td>
                    <td>{band.lane}</td>
                    <td>{band.molecularWeight}</td>
                    <td>{band.intensity}</td>
                    <td>{band.relativeQuantity}</td>
                    <td>{band.concentration}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="pagination">
              <button
                type="button"
                onClick={handlePrevious}
                disabled={currentPage === 1}
                className="page-btn"
              >
                Previous
              </button>

              <span className="page-info">
                Page {currentPage} of {totalPages}
              </span>

              <button
                type="button"
                onClick={handleNext}
                disabled={currentPage === totalPages}
                className="page-btn"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default BandTable;