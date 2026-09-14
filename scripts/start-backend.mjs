import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { resolvePython } from "./resolve-python.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");
const python = resolvePython(root);

console.log(`后端 Python: ${python.command} (${python.source})`);

const result = spawnSync(
  python.command,
  ["-m", "uvicorn", "app.main:app", "--reload", "--host", "127.0.0.1", "--port", "8000"],
  {
    cwd: path.join(root, "backend"),
    stdio: "inherit",
  },
);

process.exit(result.status ?? 1);
