import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const isWindows = process.platform === "win32";

function readCondaEnvName(root) {
  const envFile = path.join(root, "environment.yml");
  if (!fs.existsSync(envFile)) {
    return "gradetap";
  }

  const match = fs.readFileSync(envFile, "utf8").match(/^name:\s*(\S+)/m);
  return match?.[1] ?? "gradetap";
}

function findCondaExecutable() {
  if (process.env.CONDA_EXE && fs.existsSync(process.env.CONDA_EXE)) {
    return process.env.CONDA_EXE;
  }

  const lookup = spawnSync(isWindows ? "where" : "which", ["conda"], {
    encoding: "utf8",
    shell: isWindows,
  });
  if (lookup.status === 0) {
    return lookup.stdout.trim().split(/\r?\n/)[0];
  }

  const candidates = [
    "/opt/homebrew/anaconda3/bin/conda",
    "/opt/homebrew/miniconda3/bin/conda",
    "/usr/local/anaconda3/bin/conda",
    "/usr/local/miniconda3/bin/conda",
  ];
  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }

  return null;
}

function envPythonPath(envPath) {
  return isWindows
    ? path.join(envPath, "python.exe")
    : path.join(envPath, "bin", "python");
}

function findCondaEnvPython(envName) {
  const conda = findCondaExecutable();
  if (conda) {
    const baseResult = spawnSync(conda, ["info", "--base"], { encoding: "utf8" });
    if (baseResult.status === 0) {
      const candidate = envPythonPath(path.join(baseResult.stdout.trim(), "envs", envName));
      if (fs.existsSync(candidate)) {
        return candidate;
      }
    }

    const listResult = spawnSync(conda, ["env", "list"], { encoding: "utf8" });
    if (listResult.status === 0) {
      for (const line of listResult.stdout.split(/\r?\n/)) {
        const trimmed = line.trim();
        if (!trimmed || trimmed.startsWith("#")) {
          continue;
        }

        const parts = trimmed.split(/\s+/);
        const name = parts[0];
        const envPath = parts[parts.length - 1];
        if (name !== envName) {
          continue;
        }

        const candidate = envPythonPath(envPath);
        if (fs.existsSync(candidate)) {
          return candidate;
        }
      }
    }
  }

  const home = process.env.HOME || process.env.USERPROFILE;
  const commonRoots = [
    "/opt/homebrew/anaconda3",
    "/opt/homebrew/miniconda3",
    "/usr/local/anaconda3",
    "/usr/local/miniconda3",
    home && path.join(home, "anaconda3"),
    home && path.join(home, "miniconda3"),
    home && path.join(home, "opt", "anaconda3"),
  ].filter(Boolean);

  for (const base of commonRoots) {
    const candidate = envPythonPath(path.join(base, "envs", envName));
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }

  return null;
}

export function resolvePython(root) {
  if (process.env.GRADETAP_PYTHON) {
    return {
      command: process.env.GRADETAP_PYTHON,
      source: "GRADETAP_PYTHON",
    };
  }

  const condaPrefix = process.env.CONDA_PREFIX;
  if (condaPrefix && process.env.CONDA_DEFAULT_ENV !== "base") {
    const activePython = envPythonPath(condaPrefix);
    if (fs.existsSync(activePython)) {
      return {
        command: activePython,
        source: `conda (${process.env.CONDA_DEFAULT_ENV || condaPrefix})`,
      };
    }
  }

  const localCondaPython = envPythonPath(path.join(root, ".conda"));
  if (fs.existsSync(localCondaPython)) {
    return {
      command: localCondaPython,
      source: ".conda",
    };
  }

  const envName = process.env.GRADETAP_CONDA_ENV || readCondaEnvName(root);
  const condaEnvPython = findCondaEnvPython(envName);
  if (condaEnvPython) {
    return {
      command: condaEnvPython,
      source: `conda env ${envName}`,
    };
  }

  return {
    command: isWindows ? "python" : "python3",
    source: isWindows ? "python" : "python3",
  };
}
