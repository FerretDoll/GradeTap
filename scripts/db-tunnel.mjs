import { spawn } from "node:child_process";
import { readFile } from "node:fs/promises";
import net from "node:net";
import path from "node:path";
import { setTimeout as delay } from "node:timers/promises";
import { fileURLToPath } from "node:url";
import { parseEnv } from "node:util";

const host = "127.0.0.1";
const port = 13306;

function listening() {
  return new Promise((resolve) => {
    const socket = net.createConnection({ host, port });
    const finish = (ready) => {
      socket.destroy();
      resolve(ready);
    };
    socket.once("connect", () => finish(true));
    socket.once("error", () => finish(false));
    socket.setTimeout(1000, () => finish(false));
  });
}

// Only the local forwarded URL needs SSH. A server-side deployment connects directly.
export async function ensureDatabaseTunnel() {
  let databaseUrl = process.env.DATABASE_URL;
  if (!databaseUrl) {
    const env = await readFile(new URL("../backend/.env", import.meta.url), "utf8");
    databaseUrl = parseEnv(env).DATABASE_URL;
  }
  const database = new URL(databaseUrl);
  if (database.hostname !== host || database.port !== String(port)) return null;
  if (await listening()) return null;

  const child = spawn("ssh", [
    "-NT", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
    "-o", "ExitOnForwardFailure=yes", "-o", "ConnectTimeout=8",
    "-o", "ServerAliveInterval=30", "-o", "ServerAliveCountMax=3",
    "-L", `${host}:${port}:127.0.0.1:3306`, "gradetap",
  ], { stdio: ["ignore", "ignore", "inherit"], windowsHide: true });
  let launchError;
  child.once("error", (error) => { launchError = error; });
  for (let attempt = 0; attempt < 100; attempt++) {
    if (launchError) throw launchError;
    if (child.exitCode !== null || child.signalCode !== null) break;
    if (await listening()) return child;
    await delay(100);
  }
  child.kill();
  throw new Error("无法建立数据库隧道，请检查 ssh gradetap 的连接和本地 13306 端口");
}

if (path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const child = await ensureDatabaseTunnel();
  console.log(child ? "数据库隧道已建立，按 Ctrl+C 停止" : "当前数据库连接无需新建隧道");
  child?.once("exit", (code) => { process.exitCode = code ?? 0; });
}
