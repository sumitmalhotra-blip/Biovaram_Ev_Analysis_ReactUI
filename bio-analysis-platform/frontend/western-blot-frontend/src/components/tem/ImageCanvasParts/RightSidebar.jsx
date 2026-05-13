import React from "react";
import {
  FaRulerHorizontal,
  FaTable,
  FaFilter,
  FaWaveSquare,
  FaInfoCircle,
  FaQuestionCircle,
  FaDownload,
} from "react-icons/fa";
import { clamp } from "./canvasUtils";

export default function RightSidebar({
  isRightBarOpen,
  setIsRightBarOpen,
  showTable,
  viewScale,
  setViewScale,
  resetView,
  ZOOM_MIN,
  ZOOM_MAX,
  setShowHelp,
  selectedMethod,
  setSelectedMethod,
  onReanalyze,
  onShapeClassify,
  sourceFile,
  loading,
  descriptions,
  infoOpen,
  infoPos,
  toggleInfo,
  openInfo,
  closeInfo,
  setInfoOpen,
  isDrawingIntensity,
  startIntensityTool,
  minNm,
  showFilterPopup,
  handleFilterClick,
  showScalePopup,
  handleSettingsClick,
  handleTableClick,
  showGrid,
  setShowGrid,

  onExport,
  canExport = false,

  // ✅ shape actions
  onShapeGreen,
  onShapeRed,
  onShapeSkip,
  selectedCount = 0,
  shapeEnabled = false,
  imageId
}) {
  return (
    <aside className={`temRightBar ${isRightBarOpen ? "open" : "closed"}`}>
      <span>
        <button
          type="button"
          className="temRightBarToggle"
          onClick={() => setIsRightBarOpen((v) => !v)}
          title={isRightBarOpen ? "Close panel" : "Open panel"}
        >
          {isRightBarOpen ? "›" : "‹"}
        </button>

        {isRightBarOpen && <p className="head">TEM</p>}
      </span>

      <div className="temRightBarInner mt-10">
        {/* Shape actions */}
      <div className="sideGroup">
  {/* <div className="sideGroupTitle">
    Shape Actions {selectedCount > 0 ? `(${selectedCount})` : ""}
  </div> */}

  <select
    className="sideSelect"
    defaultValue=""
    onChange={(e) => {
      const value = e.target.value;

      if (!value) return;

      if (value === "classify") {
        onShapeClassify();
      } else if (value === "green") {
        onShapeGreen();
      } else if (value === "red") {
        onShapeRed();
      } else if (value === "skip") {
        onShapeSkip();
      }

      e.target.value = "";
    }}
    title={
      !sourceFile && !imageId
        ? "Upload or select an image first"
        : "Choose shape action"
    }
  >
    <option value="" disabled>
      Select Shape Action
    </option>

    <option value="classify" disabled={!sourceFile && !imageId}>
      Shape Classify
    </option>

    <option value="green" disabled={!shapeEnabled}>
      Shape Green
    </option>

    <option value="red" disabled={!shapeEnabled}>
      Shape Red
    </option>

    <option value="skip" disabled={!shapeEnabled}>
      Shape Skip
    </option>
  </select>
</div>

        {!showTable && (
          <div className="ml-10-">
            <span className="zoom-val">
              <button
                className="zoomin"
                title="Zoom out"
                onClick={() => setViewScale((z) => clamp(z * 0.9, ZOOM_MIN, ZOOM_MAX))}
                type="button"
              >
                <span className="topBtnText">−</span>
              </button>

              <button
                className="zoomin"
                title="Zoom in"
                onClick={() => setViewScale((z) => clamp(z * 1.1, ZOOM_MIN, ZOOM_MAX))}
                type="button"
              >
                <span className="topBtnText">+</span>
              </button>
            </span>

            <span className="zoom-val">
              <button className="zoom" title="Reset zoom" onClick={resetView} type="button">
                <span className="topBtnText">{Math.round(viewScale * 100)}%</span>
              </button>

              <button
                type="button"
                className="zoomin setZoom"
                onClick={() => setShowHelp(true)}
                title="Help / Shortcuts"
              >
                <FaQuestionCircle className="help-icon" />
                <span className="help-letter">Help</span>
              </button>
            </span>
          </div>
        )}

        <button
          className={`sideBtn ${showGrid ? "activeBtn" : ""}`}
          onClick={() => setShowGrid((prev) => !prev)}
          type="button"
        >
          {showGrid ? "Grid Off" : "Grid On"}
        </button>

        {/* Method select */}
        <div className="rightGroup">
          <div className="methodSelectWrap">
            <select
              className="sideSelect"
              value={selectedMethod}
              disabled={loading}
              onChange={(e) => {
                const m = e.target.value;
                setSelectedMethod(m);
                onReanalyze(m);
              }}
            >
              <option value="cnn">CNN</option>
              <option value="rulebased">Rulebased</option>
            </select>

            <FaInfoCircle
              className="methodInfoIcon"
              onClick={(e) => toggleInfo(e)}
              onMouseEnter={(e) => openInfo(e)}
              onMouseLeave={closeInfo}
            />
          </div>
        </div>

        {/* Tools */}
        <div className="rightGroup">
          <button
            onClick={startIntensityTool}
            title="Intensity line"
            className={`topBtn rightBtn ${isDrawingIntensity ? "topBtn--active" : ""}`}
            type="button"
          >
            <FaWaveSquare
              className={`topBtnIcon ${isDrawingIntensity ? "topBtnIcon--active" : ""}`}
            />
            <span className="topBtnText">Intensity</span>
          </button>

          <button
            onClick={handleFilterClick}
            title="Hide below nm"
            className={`topBtn rightBtn ${showFilterPopup ? "topBtn--active" : ""}`}
            type="button"
          >
            <FaFilter className={`topBtnIcon ${showFilterPopup ? "topBtnIcon--active" : ""}`} />
            <span className="topBtnText">{`< ${minNm}nm`}</span>
          </button>
        </div>

        <div className="d-flex">
          <button
            onClick={handleSettingsClick}
            title="Scale settings"
            className={`topBtn rightBtn ${showScalePopup ? "topBtn--active" : ""}`}
            type="button"
          >
            <FaRulerHorizontal
              className={`topBtnIcon ${showScalePopup ? "topBtnIcon--active" : ""}`}
            />
            <span className="topBtnText">Scale</span>
          </button>

          <button
            onClick={handleTableClick}
            title="Toggle table"
            className={`topBtn rightBtn ${showTable ? "topBtn--active" : ""}`}
            type="button"
          >
            <FaTable className={`topBtnIcon ${showTable ? "topBtnIcon--active" : ""}`} />
            <span className="topBtnText">Table</span>
          </button>
        </div>

        <div className="d-flex">
          <button
            onClick={onExport}
            title={canExport ? "Export report (PDF / Excel / PNG)" : "Select an image first"}
            className="topBtn rightBtn exportSideBtn"
            type="button"
            disabled={!canExport}
            style={{ width: "100%" }}
          >
            <FaDownload className="topBtnIcon" />
            <span className="topBtnText">Export</span>
          </button>
        </div>
      </div>

      {infoOpen && (
        <div
          className="methodInfoFixed"
          style={{ top: infoPos.top, left: infoPos.left }}
          onMouseEnter={() => setInfoOpen(true)}
          onMouseLeave={closeInfo}
        >
          <ul className="methodInfoList">
            {descriptions.map((t, i) => (
              <li key={i}>{t}</li>
            ))}
          </ul>
        </div>
      )}
    </aside>
  );
}