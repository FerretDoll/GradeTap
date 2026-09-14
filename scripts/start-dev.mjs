import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { resolvePython } from "./resolve-python.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");
const isWindows = process.platform === "win32";

const children = [];
let shuttingDown = false;

const python = resolvePython(root);

function resolvePnpmCommand() {
  return isWindows ? "corepack.cmd" : "corepack";
}

function logStartup() {
  console.log("GradeTap 开发环境启动中...");
  console.log(`后端 Python: ${python.command} (${python.source})`);
  console.log("后端: http://127.0.0.1:8000");
  console.log("前端: http://127.0.0.1:5173");
  console.log("按 Ctrl+C 停止\n");
}

function startProcess(name, cwd, command, args) {
  const child = spawn(command, args, {
    cwd,
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
    if (!child.killed) {
      child.kill("SIGTERM");
    }
  }

  setTimeout(() => process.exit(exitCode), 100);
}

process.on("SIGINT", () => shutdown(0));
process.on("SIGTERM", () => shutdown(0));

logStartup();

startProcess(
  "backend",
  path.join(root, "backend"),
  python.command,
  ["-m", "uvicorn", "app.main:app", "--reload", "--host", "127.0.0.1", "--port", "8000"],
);

startProcess(
  "frontend",
  path.join(root, "frontend"),
  resolvePnpmCommand(),
  ["pnpm", "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173"],
);
