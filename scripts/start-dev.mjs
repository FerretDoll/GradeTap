import { spawn, spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { resolvePython } from "./resolve-python.mjs";
import { ensureDatabaseTunnel } from "./db-tunnel.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");
const isWindows = process.platform === "win32";

const children = [];
let shuttingDown = false;

const python = resolvePython(root);

const backendPort = process.env.GRADETAP_BACKEND_PORT || "8000";
if (!/^\d+$/.test(backendPort) || Number(backendPort) < 1 || Number(backendPort) > 65535) {
  throw new Error("GRADETAP_BACKEND_PORT 必须是 1–65535 之间的端口号");
}
const backendUrl = `http://127.0.0.1:${backendPort}`;

function logStartup() {
  console.log("GradeTap 开发环境启动中...");
  console.log(`后端 Python: ${python.command} (${python.source})`);
  console.log(`后端: ${backendUrl}`);
  console.log("前端: http://127.0.0.1:5173");
  console.log("按 Ctrl+C 停止\n");
}

function startProcess(name, cwd, command, args, env = process.env) {
  const child = spawn(command, args, {
    cwd,
    env,
    stdio: "inherit",
    shell: false,
  });

  child.on("error", (error) => {
    console.error(`[${name}] 启动失败: ${error.message}`);
    shutdown(1);
  });

  child.on("exit", (code, signal) => {
    if (shuttingDown) {
      return;
    }

    const reason =
      signal != null ? `signal ${signal}` : `code ${code ?? "unknown"}`;
    console.error(`[${name}] 已退出 (${reason})`);
    shutdown(code ?? 1);
  });

  children.push(child);
  return child;
}

function shutdown(exitCode = 0) {
  if (shuttingDown) {
    return;
  }
  shuttingDown = true;

  for (const child of children) {
    if (child.pid && child.exitCode === null && child.signalCode === null && isWindows) {
      spawnSync("taskkill.exe", ["/PID", String(child.pid), "/T", "/F"], { stdio: "ignore", windowsHide: true });
    } else if (!child.killed) {
      child.kill("SIGTERM");
    }
  }

  setTimeout(() => process.exit(exitCode), 100);
}

process.on("SIGINT", () => shutdown(0));
process.on("SIGTERM", () => shutdown(0));

const tunnel = await ensureDatabaseTunnel();
if (tunnel) {
  children.push(tunnel);
  tunnel.once("exit", () => {
    if (!shuttingDown) {
      console.error("数据库隧道已关闭");
      shutdown(1);
    }
  });
}
logStartup();

startProcess(
  "backend",
  path.join(root, "backend"),
  python.command,
  ["-m", "uvicorn", "app.main:app", "--reload", "--host", "127.0.0.1", "--port", backendPort],
);

startProcess(
  "frontend",
  path.join(root, "frontend"),
  isWindows ? "cmd.exe" : "corepack",
  isWindows
    ? ["/d", "/c", "corepack.cmd pnpm run dev"]
    : ["pnpm", "run", "dev"],
  process.env.GRADETAP_BACKEND_PORT
    ? { ...process.env, VITE_API_PROXY_TARGET: backendUrl }
    : process.env,
);
