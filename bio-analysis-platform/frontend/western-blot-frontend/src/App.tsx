import { HashRouter, Routes, Route, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import TEMPage from "./pages/TEMPage";
import WesternPage from "./pages/WesternPage";
import NTAPage from "./pages/NTAPage";
import NANOFACSPage from "./pages/NANOFACSPage";
import { isTabEnabled } from "./lib/module-config";
import UpdateBanner from "./components/UpdateBanner";
import logo from "./assets/crmitlogo.png";
import temLogo from "./assets/Tem-logo-final.png";
import wblogo from "./assets/WB_Icon.png";
import temBg from "./assets/tem-background.png";
import wbBg from "./assets/wb-background.png";
import ntaIcon from "./assets/nta-icon.svg";
import nanofacsIcon from "./assets/nanofacs-icon.svg";
import { ThemeProvider, useTheme } from "./contexts/ThemeContext";
import { FaSun, FaMoon } from "react-icons/fa";

interface ModuleDef {
  id: string;
  label: string;
  sub: string;
  desc: string;
  route: string;
  color: string;       // R,G,B values e.g. "18,196,176"
  image: string | null;
  imageAlt: string;
  bgImage: string | null;
  iconText: string;
  download?: string; // Optional field to indicate if a download is needed
}

const ALL_MODULES: ModuleDef[] = [
  {
    id: "tem",
    label: "TEM Analyser",
    sub: "EV · Viability",
    desc: "Open the TEM workspace for particle review, image analysis, and viability flow.",
    route: "/tem",
    color: "18,196,176",
    image: temLogo,
    imageAlt: "TEM Icon",
    bgImage: temBg,
    iconText: "TEM",
    download: "true"
  },
  {
    id: "westernblot",
    label: "WB Analyser",
    sub: "Bands · Density",
    desc: "Open the Western Blot workspace for band detection, intensity, and result review.",
    route: "/western",
    color: "47,99,240",
    image: wblogo,
    imageAlt: "WB Icon",
    bgImage: wbBg,
    iconText: "WB",
    download: "true"
  },
  {
    id: "nta",
    label: "NTA Analyser",
    sub: "Size · Concentration",
    desc: "Open the NTA workspace for nanoparticle tracking, size distribution, and concentration analysis.",
    route: "/nta",
    color: "168,85,247",
    image: ntaIcon,
    imageAlt: "NTA Icon",
    bgImage: null,
    iconText: "NTA",
    download: "false"
  },
  {
    id: "nanofacs",
    label: "NanoFACS Analyser",
    sub: "Flow · Cytometry",
    desc: "Open the NanoFACS workspace for flow cytometry, particle gating, and multi-parameter analysis.",
    route: "/nanofacs",
    color: "249,115,22",
    image: nanofacsIcon,
    imageAlt: "NanoFACS Icon",
    bgImage: null,
    iconText: "nFACS",
    download: "false"
  },
];

  function HomePage() {
    const navigate = useNavigate();
    const { theme, toggleTheme } = useTheme();
    const [greeting, setGreeting] = useState("Good evening");
    const [launching, setLaunching] = useState("");
    const [activeSide, setActiveSide] = useState<string>("");

    const activeModules = ALL_MODULES.filter(
  (m) => m.download === "true"
);
    const gridCols = activeModules.length >= 3 ? 2 : Math.max(1, activeModules.length);
    const hasMultiRow = activeModules.length > 2;
    const imgSize   = hasMultiRow ? 80  : 170;
  const titleSize = hasMultiRow ? 18  : 34;
  const cardPad   = hasMultiRow ? "14px 18px" : "32px 20px";
  const cardGap   = hasMultiRow ? "8px"  : "14px";
  const gridGap   = hasMultiRow ? "12px" : "28px";
  const greetingMb = hasMultiRow ? "14px" : "54px";

  useEffect(() => {
    const updateClock = () => {
      const now = new Date();
      const hr = now.getHours();
      setGreeting(hr < 12 ? "Good morning" : hr < 17 ? "Good afternoon" : "Good evening");
    };

    updateClock();
    const interval = setInterval(updateClock, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleLaunch = (mod: ModuleDef) => {
    setLaunching(mod.id);
    setTimeout(() => navigate(mod.route), 350);
  };

  return (
    <div style={styles.page}>
      <style>{`
        * { box-sizing: border-box; }

        body {
          margin: 0;
          font-family: Inter, sans-serif;
          background: var(--home-body-bg);
        }

        .home-bg {
          min-height: 100vh;
          position: relative;
          overflow: hidden;
          background:
            radial-gradient(circle at center, var(--home-radial), transparent 45%),
            linear-gradient(135deg, var(--home-bg-from) 0%, var(--home-bg-to) 100%);
        }

        .split-bg {
          position: absolute;
          inset: 0;
          display: grid;
          z-index: 0;
        }

        .split-quad {
          position: relative;
          overflow: hidden;
          transition: opacity 0.35s ease;
        }

        .split-quad::before {
          content: "";
          position: absolute;
          inset: 0;
          background-position: center;
          background-repeat: no-repeat;
          background-size: cover;
          opacity: 0.14;
          transform: scale(1.04);
          transition: all 0.35s ease;
        }

        .split-quad::after {
          content: "";
          position: absolute;
          inset: 0;
          opacity: 0.35;
          transition: all 0.35s ease;
        }

        .split-quad.active::before {
          opacity: 0.30;
          transform: scale(1.08);
          filter: brightness(1.15);
        }

        .split-quad.active::after { opacity: 1; }

        .split-quad.dim::before {
          opacity: 0.04;
          filter: brightness(0.7);
        }

        .split-quad.dim::after { opacity: 0.10; }

        .split-quad[data-mod="tem"]::before {
          background-image:
            linear-gradient(to bottom right, var(--overlay-from), var(--overlay-to)),
            url("${temBg}");
        }
        .split-quad[data-mod="tem"]::after {
          background: radial-gradient(circle at 40% 50%, rgba(18,196,176,0.22), transparent 55%);
        }

        .split-quad[data-mod="westernblot"]::before {
          background-image:
            linear-gradient(to bottom left, var(--overlay-from), var(--overlay-to)),
            url("${wbBg}");
        }
        .split-quad[data-mod="westernblot"]::after {
          background: radial-gradient(circle at 60% 50%, rgba(47,99,240,0.22), transparent 55%);
        }

        .split-quad[data-mod="nta"]::before {
          background-image: linear-gradient(135deg, rgba(168,85,247,0.18), transparent 70%);
          opacity: 0.8;
        }
        .split-quad[data-mod="nta"]::after {
          background: radial-gradient(circle at 40% 60%, rgba(168,85,247,0.22), transparent 55%);
        }

        .split-quad[data-mod="nanofacs"]::before {
          background-image: linear-gradient(135deg, rgba(249,115,22,0.18), transparent 70%);
          opacity: 0.8;
        }
        .split-quad[data-mod="nanofacs"]::after {
          background: radial-gradient(circle at 60% 60%, rgba(249,115,22,0.22), transparent 55%);
        }

        .center-divider {
          position: absolute;
          top: 0;
          bottom: 0;
          left: 50%;
          width: 1px;
          transform: translateX(-50%);
          background: linear-gradient(to bottom, transparent, var(--divider-color), transparent);
          z-index: 1;
        }

        .top-bar {
          position: fixed;
          top: 20px;
          left: 24px;
          right: 24px;
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          z-index: 20;
        }

        .logo-wrap { display: flex; align-items: center; }

        .logo {
          height: 64px;
          width: auto;
          object-fit: contain;
          display: block;
        }

        .clock { text-align: right; }

        .clock-time {
          font-size: 14px;
          font-weight: 500;
          color: var(--clock-time-color);
          font-variant-numeric: tabular-nums;
        }

        .clock-date {
          font-family: monospace;
          font-size: 10px;
          color: var(--clock-date-color);
          margin-top: 2px;
        }

        .content-shell {
          position: relative;
          z-index: 5;
          min-height: 100vh;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: ${hasMultiRow ? "0px 20px 25px" : "25px 20px 40px"};
        }

        .greeting-label {
          font-family: monospace;
          font-size: ${hasMultiRow ? "10px" : "11px"};
          letter-spacing: 0.22em;
          color: var(--greeting-label-color);
          text-transform: uppercase;
          margin-bottom: ${hasMultiRow ? "6px" : "10px"};
        }

        .greeting-title {
          font-size: ${hasMultiRow ? "22px" : "28px"};
          font-weight: 300;
          color: var(--greeting-title-color);
          letter-spacing: -0.02em;
          margin-bottom: ${greetingMb};
          text-align: center;
        }

        .greeting-title strong {
          font-weight: 700;
          color: var(--greeting-strong-color);
        }

        .modules-grid {
          width: min(1200px, calc(100% - 40px));
          display: grid;
          gap: ${gridGap};
          align-items: stretch;
          justify-content: center;
        }

        .panel-btn {
          position: relative;
          width: 100%;
          min-height: 0;
          border: 1px solid var(--panel-border);
          border-radius: ${hasMultiRow ? "24px" : "32px"};
          background: var(--panel-bg, transparent);
          backdrop-filter: blur(16px);
          box-shadow: var(--panel-card-shadow, none);
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          gap: ${cardGap};
          cursor: pointer;
          transition: transform 0.28s ease, box-shadow 0.28s ease, border-color 0.28s ease;
          overflow: hidden;
          padding: ${cardPad};
        }

        .panel-btn:hover {
          transform: translateY(-6px);
          border-color: var(--mod-border-color, rgba(255,255,255,0.2));
          box-shadow: var(--mod-shadow, 0 20px 60px rgba(0,0,0,0.2));
        }

        .panel-btn.active {
          border-color: var(--mod-border-color, rgba(255,255,255,0.2));
          box-shadow: var(--mod-shadow, 0 20px 60px rgba(0,0,0,0.2));
        }

        .panel-glow {
          position: absolute;
          width: 220px;
          height: 220px;
          border-radius: 50%;
          filter: blur(50px);
          opacity: 0.18;
          z-index: 0;
          transition: opacity 0.28s ease, transform 0.28s ease;
        }

        .panel-btn:hover .panel-glow,
        .panel-btn.active .panel-glow {
          opacity: 0.3;
          transform: scale(1.08);
        }

        .tool-card-image-wrap {
          position: relative;
          z-index: 1;
          width: ${imgSize}px;
          height: ${imgSize}px;
          border-radius: ${hasMultiRow ? "18px" : "28px"};
          overflow: hidden;
          box-shadow: 0 ${hasMultiRow ? 10 : 18}px ${hasMultiRow ? 30 : 50}px rgba(0,0,0,0.28);
          flex-shrink: 0;
        }

        .tool-card-image {
          width: 100%;
          height: 100%;
          object-fit: cover;
          display: block;
        }

        .module-icon-fallback {
          width: 100%;
          height: 100%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: ${hasMultiRow ? 22 : 36}px;
          font-weight: 800;
          letter-spacing: -0.03em;
          color: #fff;
        }

        .panel-title {
          position: relative;
          z-index: 1;
          font-size: ${titleSize}px;
          font-weight: 700;
          color: var(--panel-title-color);
          margin-top: ${hasMultiRow ? "2px" : "6px"};
        }

        .panel-sub {
          position: relative;
          z-index: 1;
          font-size: ${hasMultiRow ? "11px" : "13px"};
          color: var(--panel-sub-color);
          letter-spacing: 0.04em;
        }

        .panel-desc {
          position: relative;
          z-index: 1;
          max-width: ${hasMultiRow ? "260px" : "300px"};
          text-align: center;
          font-size: ${hasMultiRow ? "11px" : "13px"};
          line-height: 1.5;
          color: var(--panel-desc-color);
          display: -webkit-box;
          -webkit-line-clamp: ${hasMultiRow ? 2 : 10};
          -webkit-box-orient: vertical;
          overflow: hidden;
        }

        .version-corner {
          margin-top: ${hasMultiRow ? "10px" : "28px"};
          font-family: monospace;
          font-size: 10px;
          color: var(--clock-date-color);
          opacity: 0.6;
        }

        @media (max-width: 900px) {
          .modules-grid {
            grid-template-columns: 1fr 1fr !important;
            gap: 12px;
          }
          .split-bg {
            grid-template-columns: 1fr 1fr !important;
            grid-template-rows: ${hasMultiRow ? "1fr 1fr" : "1fr"} !important;
          }
        }

        @media (max-width: 600px) {
          .modules-grid { grid-template-columns: 1fr !important; }
          .split-bg {
            grid-template-columns: 1fr !important;
            grid-template-rows: unset !important;
          }
          .center-divider { display: none; }
          .tool-card-image-wrap { width: 100px !important; height: 100px !important; }
          .panel-title { font-size: 20px !important; }
          .top-bar { top: 16px; left: 16px; right: 16px; }
          .logo { height: 44px; }
          .greeting-title { font-size: 20px; margin-bottom: 12px; }
        }
      `}</style>

      <div className="home-bg">
        <div
          className="split-bg"
          style={{
            gridTemplateColumns: `repeat(${gridCols}, 1fr)`,
            gridTemplateRows: hasMultiRow ? "1fr 1fr" : "1fr",
          }}
        >
          {activeModules.map((mod) => (
            <div
              key={mod.id}
              data-mod={mod.id}
              className={`split-quad ${
                activeSide === mod.id ? "active" : activeSide ? "dim" : ""
              }`}
            />
          ))}
        </div>

        <div className="center-divider" />

        <div className="top-bar">
          <div className="logo-wrap">
            <img src={logo} alt="CRMIT Logo" className="logo" />
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <button
              className="theme-toggle-btn"
              onClick={toggleTheme}
              title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
            >
              {theme === "dark" ? <FaSun /> : <FaMoon />}
            </button>
          </div>
        </div>

        <div className="content-shell">
          <div className="greeting-label">{greeting}</div>
          <div className="greeting-title">
            Welcome to <strong>EVAR</strong>
          </div>

          <div
            className="modules-grid"
            style={{ gridTemplateColumns: `repeat(${gridCols}, 1fr)` }}
          >
            {activeModules.map((mod) => (
              <button
                key={mod.id}
                className={`panel-btn ${launching === mod.id ? "active" : ""}`}
                type="button"
                onMouseEnter={() => setActiveSide(mod.id)}
                onMouseLeave={() => setActiveSide("")}
                onClick={() => handleLaunch(mod)}
                style={
                  {
                    "--mod-border-color": `rgba(${mod.color},0.35)`,
                    "--mod-shadow": `0 20px 60px rgba(${mod.color},0.22)`,
                  } as React.CSSProperties
                }
              >
                <div
                  className="panel-glow"
                  style={{ background: `rgba(${mod.color},0.75)` }}
                />
                <div className="tool-card-image-wrap">
                  {mod.image ? (
                    <img
                      src={mod.image}
                      alt={mod.imageAlt}
                      className="tool-card-image"
                    />
                  ) : (
                    <div
                      className="module-icon-fallback"
                      style={{
                        background: `linear-gradient(135deg, rgba(${mod.color},0.9) 0%, rgba(${mod.color},0.5) 100%)`,
                      }}
                    >
                      {mod.iconText}
                    </div>
                  )}
                </div>
                <div className="panel-title">{mod.label}</div>
                <div className="panel-sub">{mod.sub}</div>
                <div className="panel-desc">{mod.desc}</div>
              </button>
            ))}
          </div>

          <div className="version-corner">
            {window.electronBridge?.appVersion
              ? `v${window.electronBridge.appVersion}`
              : "v1.0"}
          </div>
        </div>
      </div>
    </div>
  );
}

const styles: { [key: string]: React.CSSProperties } = {
  page: {
    minHeight: "100vh",
    background: "var(--home-body-bg)",
  },
};

export default function App() {
  return (
    <ThemeProvider>
      <HashRouter>
        <UpdateBanner />
        <Routes>
          <Route path="/" element={<HomePage />} />
          {isTabEnabled("tem") && (
            <Route path="/tem" element={<TEMPage />} />
          )}
          {isTabEnabled("westernblot") && (
            <Route path="/western" element={<WesternPage />} />
          )}
          {isTabEnabled("nta") && (
            <Route path="/nta" element={<NTAPage />} />
          )}
          {isTabEnabled("nanofacs") && (
            <Route path="/nanofacs" element={<NANOFACSPage />} />
          )}
        </Routes>
      </HashRouter>
    </ThemeProvider>
  );
}
