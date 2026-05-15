import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { FaCog, FaSun, FaMoon } from "react-icons/fa";
import { useTheme } from "../contexts/ThemeContext";
import nanofacsIcon from "../assets/nanofacs-icon.svg";

export default function NANOFACSPage() {
  const [openMenu, setOpenMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setOpenMenu(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div style={{ background: "var(--app-bg)", minHeight: "100vh" }}>
      <div className="page-header-wrap">
        <h2 className="temTitle page-head">NanoFACS Analysis</h2>

        <div className="header-menu" ref={menuRef}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <button
              className="theme-toggle-btn"
              onClick={toggleTheme}
              title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
            >
              {theme === "dark" ? <FaSun /> : <FaMoon />}
            </button>
            <button
              className="icon-btn"
              onClick={() => setOpenMenu((prev) => !prev)}
              type="button"
            >
              <FaCog style={{ fontSize: "16px" }} />
            </button>
          </div>

          {openMenu && (
            <div className="dropdown-menu">
              <button
                className="dropdown-item"
                onClick={() => { setOpenMenu(false); navigate("/"); }}
                type="button"
              >
                Home
              </button>
              <button
                className="dropdown-item"
                onClick={() => { setOpenMenu(false); navigate("/tem"); }}
                type="button"
              >
                TEM Analyser
              </button>
              <button
                className="dropdown-item"
                onClick={() => { setOpenMenu(false); navigate("/western"); }}
                type="button"
              >
                WB Analyser
              </button>
              <button
                className="dropdown-item"
                onClick={() => { setOpenMenu(false); navigate("/nta"); }}
                type="button"
              >
                NTA Analyser
              </button>
            </div>
          )}
        </div>
      </div>

      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          minHeight: "calc(100vh - 80px)",
          gap: "16px",
          color: "var(--panel-title-color)",
          textAlign: "center",
          padding: "40px 20px",
        }}
      >
        <img
          src={nanofacsIcon}
          alt="NanoFACS Icon"
          style={{
            width: 100,
            height: 100,
            borderRadius: 24,
            boxShadow: "0 12px 40px rgba(249,115,22,0.4)",
            marginBottom: 8,
          }}
        />
        <h2 style={{ fontSize: 28, fontWeight: 700, margin: 0 }}>NanoFACS Analyser</h2>
        <p style={{ fontSize: 14, color: "var(--panel-desc-color)", maxWidth: 380, lineHeight: 1.7 }}>
          The NanoFACS flow cytometry module is initialising. Connect to the NanoFACS
          backend service to begin particle gating and multi-parameter analysis.
        </p>
      </div>
    </div>
  );
}
