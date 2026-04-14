const fs = require("fs");
const http = require("http");
const { spawn } = require("child_process");
const path = require("path");
const {
  DEFAULT_BACKEND_PORT,
  BACKEND_HEALTH_TIMEOUT_MS,
  BACKEND_HEALTH_POLL_MS,
  getDevBackendPython,
  getDevBackendEntry,
  getBundledBackendExe,
} = require("./constants");

class BackendManager {
  constructor({ isPackaged, logger }) {
    this.isPackaged = isPackaged;
    this.log = logger;
    this.process = null;
    this.port = Number(process.env.CRMIT_PORT || DEFAULT_BACKEND_PORT);
    this.starting = false;
  }

  async start() {
    if (this.process || this.starting) {
      return;
    }

    this.starting = true;
    try {
      const commandInfo = this._resolveCommand();
      this.log.info(`Starting backend: ${commandInfo.command} ${commandInfo.args.join(" ")}`);

      const env = {
        ...process.env,
        CRMIT_PORT: String(this.port),
        CRMIT_PORT_STRICT: "1",
        CRMIT_NO_BROWSER: "1",
        CRMIT_ELECTRON_HOST: "1",
      };

      this.process = spawn(commandInfo.command, commandInfo.args, {
        cwd: commandInfo.cwd,
        env,
        windowsHide: true,
        stdio: ["ignore", "pipe", "pipe"],
      });

      this.process.stdout.on("data", (data) => {
        this.log.info(`[backend] ${String(data).trimEnd()}`);
      });

      this.process.stderr.on("data", (data) => {
        this.log.error(`[backend] ${String(data).trimEnd()}`);
      });

      this.process.on("exit", (code, signal) => {
        this.log.info(`Backend exited (code=${code}, signal=${signal})`);
        this.process = null;
      });

      await this._waitUntilHealthy();
      this.log.info(`Backend is healthy on http://127.0.0.1:${this.port}`);
    } finally {
      this.starting = false;
    }
  }

  async stop() {
    if (!this.process) {
      return;
    }

    const pid = this.process.pid;
    this.log.info(`Stopping backend process pid=${pid}`);

    await new Promise((resolve) => {
      const timer = setTimeout(() => {
        resolve();
      }, 8000);

      this.process.once("exit", () => {
        clearTimeout(timer);
        resolve();
      });

      if (process.platform === "win32") {
        spawn("taskkill", ["/PID", String(pid), "/T", "/F"], { windowsHide: true });
      } else {
        this.process.kill("SIGTERM");
      }
    });

    this.process = null;
  }

  getBaseUrl() {
    return `http://127.0.0.1:${this.port}`;
  }

  _resolveCommand() {
    if (this.isPackaged) {
      const backendExe = getBundledBackendExe();
      if (!fs.existsSync(backendExe)) {
        throw new Error(`Bundled backend executable not found: ${backendExe}`);
      }
      return {
        command: backendExe,
        args: [],
        cwd: path.dirname(backendExe),
      };
    }

    const pythonExe = getDevBackendPython();
    const backendEntry = getDevBackendEntry();

    if (!fs.existsSync(pythonExe)) {
      throw new Error(`Backend Python interpreter not found: ${pythonExe}`);
    }
    if (!fs.existsSync(backendEntry)) {
      throw new Error(`Backend desktop entrypoint not found: ${backendEntry}`);
    }

    return {
      command: pythonExe,
      args: [backendEntry],
      cwd: path.dirname(backendEntry),
    };
  }

  async _waitUntilHealthy() {
    const started = Date.now();

    while (Date.now() - started < BACKEND_HEALTH_TIMEOUT_MS) {
      const healthy = await this._probeHealth();
      if (healthy) {
        return;
      }

      if (!this.process) {
        throw new Error("Backend process exited before becoming healthy");
      }

      await new Promise((resolve) => setTimeout(resolve, BACKEND_HEALTH_POLL_MS));
    }

    throw new Error(`Backend health check timed out after ${BACKEND_HEALTH_TIMEOUT_MS} ms`);
  }

  _probeHealth() {
    const url = `${this.getBaseUrl()}/health`;

    return new Promise((resolve) => {
      const req = http.get(url, (res) => {
        res.resume();
        resolve(res.statusCode === 200);
      });

      req.on("error", () => resolve(false));
      req.setTimeout(2000, () => {
        req.destroy();
        resolve(false);
      });
    });
  }
}

module.exports = { BackendManager };
