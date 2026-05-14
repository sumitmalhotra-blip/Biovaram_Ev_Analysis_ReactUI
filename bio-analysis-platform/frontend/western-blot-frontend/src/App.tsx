import { HashRouter, Routes, Route, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import TEMPage from "./pages/TEMPage";
import WesternPage from "./pages/WesternPage";
import { isTabEnabled } from "./lib/module-config";
import UpdateBanner from "./components/UpdateBanner";
import logo from "./assets/crmitlogo.png";
import temLogo from "./assets/Tem-logo-final.png";
import wblogo from "./assets/WB_Icon.png";
import temBg from "./assets/tem-background.png";
import wbBg from "./assets/wb-background.png";
import { ThemeProvider, useTheme } from "./contexts/ThemeContext";
import { FaSun, FaMoon } from "react-icons/fa";

function HomePage() {
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();
  const [time, setTime] = useState("--:--");
  const [date, setDate] = useState("---");
  const [greeting, setGreeting] = useState("Good evening");
  const [launching, setLaunching] = useState("");
  const [activeSide, setActiveSide] = useState<"tem" | "western" | "">("");

  useEffect(() => {
    const updateClock = () => {
      const now = new Date();

      const h = String(now.getHours()).padStart(2, "0");
      const m = String(now.getMinutes()).padStart(2, "0");
      setTime(`${h}:${m}`);

      const days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
      const months = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
      ];

      setDate(`${days[now.getDay()]} · ${months[now.getMonth()]} ${now.getDate()}`);

      const hr = now.getHours();
      setGreeting(
        hr < 12 ? "Good morning" : hr < 17 ? "Good afternoon" : "Good evening"
      );
    };

    updateClock();
    const interval = setInterval(updateClock, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleLaunch = (tool: string) => {
    setLaunching(tool);
    setTimeout(() => {
      navigate(tool === "tem" ? "/tem" : "/western");
    }, 350);
  };

  return (
    <div style={styles.page}>
      <style>{`
        * {
          box-sizing: border-box;
        }

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
          display: flex;
          z-index: 0;
        }

        .split-half {
          width: 50%;
          height: 100%;
          position: relative;
          overflow: hidden;
          transition: all 0.35s ease;
        }

        .split-half::before {
          content: "";
          position: absolute;
          inset: 0;
          background-position: center;
          background-repeat: no-repeat;
          background-size: cover;
          opacity: var(--bg-img-opacity, 0.14);
          transform: scale(1.04);
          transition: all 0.35s ease;
        }

        .split-half::after {
          content: "";
          position: absolute;
          inset: 0;
          transition: all 0.35s ease;
        }

        .split-half.tem::before {
          background-image:
            linear-gradient(to right, var(--overlay-from), var(--overlay-to)),
            url("${temBg}");
        }

        .split-half.wb::before {
          background-image:
            linear-gradient(to left, var(--overlay-from), var(--overlay-to)),
            url("${wbBg}");
        }

        .split-half.tem::after {
          background:
            radial-gradient(circle at 40% 50%, rgba(18,196,176,0.22), transparent 48%);
          opacity: 0.35;
        }

        .split-half.wb::after {
          background:
            radial-gradient(circle at 60% 50%, rgba(47,99,240,0.22), transparent 48%);
          opacity: 0.35;
        }

        .split-half.active::before {
          opacity: 0.32;
          transform: scale(1.08);
          filter: brightness(1.15);
        }

        .split-half.active::after {
          opacity: 1;
        }

        .split-half.dim::before {
          opacity: 0.06;
          filter: brightness(0.7);
        }

        .split-half.dim::after {
          opacity: 0.14;
        }

        .center-divider {
          position: absolute;
          top: 0;
          bottom: 0;
          left: 50%;
          width: 1px;
          transform: translateX(-50%);
          background: linear-gradient(
            to bottom,
            transparent,
            var(--divider-color),
            transparent
          );
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

        .logo-wrap {
          display: flex;
          align-items: center;
        }

        .logo {
          height: 64px;
          width: auto;
          object-fit: contain;
          display: block;
        }

        .clock {
          text-align: right;
        }

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
          padding: 25px 20px 40px;
        }

        .greeting-label {
          font-family: monospace;
          font-size: 11px;
          letter-spacing: 0.22em;
          color: var(--greeting-label-color);
          text-transform: uppercase;
          margin-bottom: 10px;
        }

        .greeting-title {
          font-size: 28px;
          font-weight: 300;
          color: var(--greeting-title-color);
          letter-spacing: -0.02em;
          margin-bottom: 54px;
          text-align: center;
        }

        .greeting-title strong {
          font-weight: 700;
          color: var(--greeting-strong-color);
        }

        .split-row {
          width: min(1100px, 100%);
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 32px;
          align-items: stretch;
        }

        .panel-btn {
          position: relative;
          min-height: 360px;
          border: 1px solid var(--panel-border);
          border-radius: 32px;
          background: var(--panel-bg, transparent);
          backdrop-filter: blur(16px);
          box-shadow: var(--panel-card-shadow, none);
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          gap: 14px;
          cursor: pointer;
          transition: transform 0.28s ease, box-shadow 0.28s ease, border-color 0.28s ease;
          overflow: hidden;
          padding: 32px 20px;
        }

        .panel-btn:hover {
          transform: translateY(-6px);
        }

        .panel-btn.tem-panel:hover,
        .panel-btn.tem-panel.active {
          border-color: rgba(18,196,176,0.35);
          box-shadow: 0 20px 60px rgba(18,196,176,0.22);
        }

        .panel-btn.wb-panel:hover,
        .panel-btn.wb-panel.active {
          border-color: rgba(47,99,240,0.35);
          box-shadow: 0 20px 60px rgba(47,99,240,0.22);
        }

        .panel-glow {
          position: absolute;
          inset: auto;
          width: 220px;
          height: 220px;
          border-radius: 50%;
          filter: blur(50px);
          opacity: 0.18;
          z-index: 0;
          transition: opacity 0.28s ease, transform 0.28s ease;
        }

        .tem-panel .panel-glow {
          background: rgba(18,196,176,0.75);
        }

        .wb-panel .panel-glow {
          background: rgba(47,99,240,0.75);
        }

        .panel-btn:hover .panel-glow,
        .panel-btn.active .panel-glow {
          opacity: 0.3;
          transform: scale(1.08);
        }

        .tool-card-image-wrap {
          position: relative;
          z-index: 1;
          width: 170px;
          height: 170px;
          border-radius: 30px;
          overflow: hidden;
          box-shadow: 0 18px 50px rgba(0,0,0,0.28);
        }

        .tool-card-image {
          width: 100%;
          height: 100%;
          object-fit: cover;
          display: block;
        }

        .panel-title {
          position: relative;
          z-index: 1;
          font-size: 34px;
          font-weight: 700;
          color: var(--panel-title-color);
          margin-top: 8px;
        }

        .panel-sub {
          position: relative;
          z-index: 1;
          font-size: 14px;
          color: var(--panel-sub-color);
          letter-spacing: 0.04em;
        }

        .panel-desc {
          position: relative;
          z-index: 1;
          max-width: 320px;
          text-align: center;
          font-size: 13px;
          line-height: 1.6;
          color: var(--panel-desc-color);
        }

        .dock {
          margin-top: 36px;
          background: var(--dock-bg);
          border: 1px solid var(--dock-border);
          backdrop-filter: blur(16px);
          border-radius: 16px;
          padding: 10px 22px;
          display: flex;
          align-items: center;
          gap: 0;
          flex-wrap: wrap;
          justify-content: center;
          z-index: 2;
        }

        .dock-item {
          display: flex;
          align-items: center;
          gap: 6px;
          font-family: monospace;
          font-size: 10px;
          color: var(--dock-text);
          padding: 0 16px;
        }

        .dock-sep {
          width: 1px;
          height: 16px;
          background: var(--dock-sep);
        }

        .dock-dot {
          width: 6px;
          height: 6px;
          border-radius: 50%;
        }

        .dock-dot.g {
          background: #22c55e;
        }

        .dock-dot.b {
          background: #3b82f6;
        }

        @media (max-width: 900px) {
          .split-row {
            grid-template-columns: 1fr;
            gap: 20px;
          }

          .panel-btn {
            min-height: 300px;
          }

          .split-bg {
            flex-direction: column;
          }

          .split-half {
            width: 100%;
            height: 50%;
          }

          .center-divider {
            display: none;
          }
        }

        @media (max-width: 768px) {
          .top-bar {
            top: 16px;
            left: 16px;
            right: 16px;
          }

          .logo {
            height: 44px;
          }

          .clock-time {
            font-size: 12px;
          }

          .clock-date {
            font-size: 9px;
          }

          .greeting-title {
            font-size: 22px;
            margin-bottom: 32px;
          }

          .tool-card-image-wrap {
            width: 140px;
            height: 140px;
          }

          .panel-title {
            font-size: 28px;
          }
        }
      `}</style>

      <div className="home-bg">
        <div className="split-bg">
          <div
            className={`split-half tem ${
              activeSide === "tem" ? "active" : activeSide === "western" ? "dim" : ""
            }`}
          />
          <div
            className={`split-half wb ${
              activeSide === "western" ? "active" : activeSide === "tem" ? "dim" : ""
            }`}
          />
        </div>

        <div className="center-divider" />

        <div className="top-bar">
  <div className="logo-wrap">
    <img src={logo} alt="CRMIT Logo" className="logo" />
  </div>

  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
    <button className="theme-toggle-btn" onClick={toggleTheme} title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}>
      {theme === "dark" ? <FaSun /> : <FaMoon />}
    </button>
  </div>
</div>
        
        

        <div className="content-shell">
          <div className="greeting-label">{greeting}</div>
          <div className="greeting-title">
            Welcome to <strong>EVAR</strong>
          </div>
          

          <div className="split-row">

            {/* ── CHANGE 2: TEM button gated by module profile ── */}
            {isTabEnabled("tem") && (
              <button
                className={`panel-btn tem-panel ${launching === "tem" ? "active" : ""}`}
                type="button"
                onMouseEnter={() => setActiveSide("tem")}
                onMouseLeave={() => setActiveSide("")}
                onClick={() => handleLaunch("tem")}
              >
                <div className="panel-glow" />
                <div className="tool-card-image-wrap">
                  <img src={temLogo} alt="TEM Icon" className="tool-card-image" />
                </div>
                <div className="panel-title">TEM Analyser</div>
                <div className="panel-sub">EV · Viability</div>
                <div className="panel-desc">
                  Open the TEM workspace for particle review, image analysis, and viability flow.
                </div>
              </button>
            )}

            {/* ── CHANGE 3: WB button gated by module profile ── */}
            {isTabEnabled("westernblot") && (
              <button
                className={`panel-btn wb-panel ${launching === "western" ? "active" : ""}`}
                type="button"
                onMouseEnter={() => setActiveSide("western")}
                onMouseLeave={() => setActiveSide("")}
                onClick={() => handleLaunch("western")}
              >
                <div className="panel-glow" />
                <div className="tool-card-image-wrap">
                  <img src={wblogo} alt="WB Icon" className="tool-card-image" />
                </div>
                <div className="panel-title">WB Analyser</div>
                <div className="panel-sub">Bands · Density</div>
                <div className="panel-desc">
                  Open the Western Blot workspace for band detection, intensity, and result review.
                </div>
              </button>
            )}

          </div>
          <div className="version-corner">
            {window.electronBridge?.appVersion ? `v${window.electronBridge.appVersion}` : 'v1.0'}
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
        </Routes>
      </HashRouter>
    </ThemeProvider>
  );
}
