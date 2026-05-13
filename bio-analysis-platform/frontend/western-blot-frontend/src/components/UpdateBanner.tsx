import { useEffect, useState } from "react";

// ---------------------------------------------------------------------------
// Global type augmentation for the Electron preload bridge
// ---------------------------------------------------------------------------
declare global {
  interface Window {
    electronBridge?: {
      appVersion: string;
      updater: {
        onUpdateAvailable: (
          cb: (info: { version: string; releaseNotes?: string }) => void
        ) => void;
        onUpdateDownloaded: (cb: (info: { version: string }) => void) => void;
        onDownloadProgress: (
          cb: (progress: {
            percent: number;
            transferred: number;
            total: number;
          }) => void
        ) => void;
        onUpdateError: (cb: (msg: string) => void) => void;
        installUpdate: () => void;
        getUpdateState: () => Promise<{
          status: "idle" | "available" | "downloading" | "ready";
          info: { version: string } | null;
          progress: { percent: number; transferred: number; total: number } | null;
        }>;
      };
    };
  }
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
type Status = "idle" | "available" | "downloading" | "ready";

// ---------------------------------------------------------------------------
// Inline style constants
// ---------------------------------------------------------------------------
const BANNER_BASE: React.CSSProperties = {
  position: "fixed",
  top: 0,
  left: 0,
  right: 0,
  zIndex: 9999,
  height: 44,
  background: "rgba(15,20,35,0.97)",
  borderBottom: "1px solid rgba(255,255,255,0.08)",
  backdropFilter: "blur(12px)",
  WebkitBackdropFilter: "blur(12px)",
  display: "flex",
  flexDirection: "row",
  alignItems: "center",
  justifyContent: "space-between",
  padding: "0 20px",
  boxSizing: "border-box",
  fontFamily: "inherit",
};

const LEFT_SIDE: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 10,
  fontSize: 13,
  color: "rgba(255,255,255,0.88)",
  fontWeight: 500,
  letterSpacing: 0.1,
};

const RIGHT_SIDE: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 8,
};

function dot(color: string, pulse = false): React.CSSProperties {
  return {
    width: 8,
    height: 8,
    borderRadius: "50%",
    background: color,
    flexShrink: 0,
    animation: pulse ? "biolabPulse 1.2s ease-in-out infinite" : undefined,
  };
}

function actionButton(bg: string): React.CSSProperties {
  return {
    height: 28,
    padding: "0 12px",
    borderRadius: 5,
    border: "none",
    background: bg,
    color: "#fff",
    fontSize: 12,
    fontWeight: 600,
    cursor: "pointer",
    letterSpacing: 0.2,
    lineHeight: "28px",
  };
}

const LATER_BUTTON: React.CSSProperties = {
  height: 28,
  padding: "0 10px",
  borderRadius: 5,
  border: "1px solid rgba(255,255,255,0.18)",
  background: "transparent",
  color: "rgba(255,255,255,0.55)",
  fontSize: 12,
  fontWeight: 500,
  cursor: "pointer",
  letterSpacing: 0.1,
  lineHeight: "26px",
};

const DISMISS_BUTTON: React.CSSProperties = {
  width: 24,
  height: 24,
  borderRadius: 4,
  border: "none",
  background: "transparent",
  color: "rgba(255,255,255,0.45)",
  fontSize: 16,
  cursor: "pointer",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  padding: 0,
  lineHeight: 1,
};

// Keyframe injection — runs once
let _keyframesInjected = false;
function injectKeyframes() {
  if (_keyframesInjected || typeof document === "undefined") return;
  _keyframesInjected = true;
  const style = document.createElement("style");
  style.textContent = `
    @keyframes biolabPulse {
      0%, 100% { opacity: 1; transform: scale(1); }
      50%       { opacity: 0.4; transform: scale(0.75); }
    }
  `;
  document.head.appendChild(style);
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
export default function UpdateBanner() {
  const [status, setStatus] = useState<Status>("idle");
  const [newVersion, setNewVersion] = useState("");
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    injectKeyframes();

    const updater = window.electronBridge?.updater;
    if (!updater) return;

    // Fetch cached state from main process — handles race condition where
    // update-available fired before this component mounted its listeners
    updater.getUpdateState?.().then((state) => {
      if (!state) return;
      if (state.status === "available" && state.info) {
        setNewVersion(state.info.version);
        setStatus("available");
      } else if (state.status === "downloading" && state.info) {
        setNewVersion(state.info.version);
        setProgress(Math.round(state.progress?.percent ?? 0));
        setStatus("downloading");
      } else if (state.status === "ready" && state.info) {
        setNewVersion(state.info.version);
        setProgress(100);
        setStatus("ready");
      }
    });

    // Also listen for future events
    updater.onUpdateAvailable((info) => {
      setNewVersion(info.version);
      setStatus("available");
    });

    updater.onDownloadProgress((p) => {
      setProgress(Math.round(p.percent));
      setStatus("downloading");
    });

    updater.onUpdateDownloaded((info) => {
      setNewVersion(info.version);
      setProgress(100);
      setStatus("ready");
    });

    updater.onUpdateError(() => {
      setStatus("idle");
    });
  }, []);

  if (status === "idle") return null;

  const dismiss = () => setStatus("idle");

  return (
    <div style={{ ...BANNER_BASE }}>
      {/* Progress bar — only visible while downloading */}
      {status === "downloading" && (
        <div
          style={{
            position: "absolute",
            bottom: 0,
            left: 0,
            height: 2,
            width: `${progress}%`,
            background: "#2f63f0",
            transition: "width 0.3s ease",
          }}
        />
      )}

      {/* Left side */}
      <div style={LEFT_SIDE}>
        {status === "available" && (
          <>
            <span style={dot("#12c4b0")} />
            <span>EVAR {newVersion} is available — downloading in background</span>
          </>
        )}
        {status === "downloading" && (
          <>
            <span style={dot("#2f63f0", true)} />
            <span>Downloading update… {progress}%</span>
          </>
        )}
        {status === "ready" && (
          <>
            <span style={dot("#22c55e")} />
            <span>Update ready — restart to apply</span>
          </>
        )}
      </div>

      {/* Right side */}
      <div style={RIGHT_SIDE}>
        {status === "available" && (
          <button style={DISMISS_BUTTON} onClick={dismiss} title="Dismiss">
            ×
          </button>
        )}
        {status === "ready" && (
          <>
            <button
              style={actionButton("#22c55e")}
              onClick={() => window.electronBridge?.updater?.installUpdate()}
            >
              Restart Now
            </button>
            <button style={LATER_BUTTON} onClick={dismiss}>
              Later
            </button>
          </>
        )}
      </div>
    </div>
  );
}
