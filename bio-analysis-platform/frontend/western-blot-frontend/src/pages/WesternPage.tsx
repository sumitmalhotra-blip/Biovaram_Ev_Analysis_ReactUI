// // import React from "react";
// 

// export default function WesternPage() {
//   return (
//     <div style={{ padding: "20px" }}>
//       <h2>Western Blot Analysis</h2>
//       <WesternModule />
//     </div>
//   );
// }

// import React from "react";


// import { FaCog } from "react-icons/fa";

// export default function TEMPage() {
//   return (
//     <div style={{ padding: "20px" }}>
//       <div className="page-header-wrap">
//     <h2 className="page-header">TEM Analysis</h2>
    
// </div>
// <FaCog className="logOut" />
//       <Tem />
//     </div>
//   );
// }
// @ts-ignore
import WesternModule from "../components/western/WesternModule";
import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { FaCog, FaSun, FaMoon } from "react-icons/fa";
import { useTheme } from "../contexts/ThemeContext";
// import Tem from "./Tem";

export default function TEMPage() {
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
    <div>
      <div className="page-header-wrap">
        <h2 className="wbTitle page-head">Western Blot Analysis</h2>

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
                Logout
              </button>
              <button
                className="dropdown-item"
                onClick={() => { setOpenMenu(false); navigate("/tem"); }}
                type="button"
              >
                TEM Analyser
              </button>
            </div>
          )}
        </div>
      </div>

      <WesternModule />
    </div>
  );
}