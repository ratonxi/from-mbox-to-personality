#!/usr/bin/env node
const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawnSync } = require("child_process");

const repoRoot = path.resolve(__dirname, "..");
const skillName = "from-mbox-to-personality";
const skillSource = path.join(repoRoot, "skills", skillName);

function usage() {
  console.log(`From MBOX to Personality

Usage:
  from-mbox-to-personality install-skill [--codex-home <path>] [--force]
  from-mbox-to-personality run -- --mbox <file.mbox> --out <dir> [--target-email <email>]

Fast install from GitHub:
  npx github:ratonxi/from-mbox-to-personality install-skill

Commands:
  install-skill  Copy the Codex skill into CODEX_HOME/skills.
  run            Run the bundled Python wrapper. Pass wrapper args after --.
`);
}

function parseFlag(args, flag) {
  const index = args.indexOf(flag);
  if (index === -1) return null;
  return args[index + 1] || null;
}

function codexHome(args) {
  return parseFlag(args, "--codex-home") || process.env.CODEX_HOME || path.join(os.homedir(), ".codex");
}

function copyRecursive(src, dest, force) {
  if (!fs.existsSync(src)) {
    throw new Error(`Missing source: ${src}`);
  }
  if (fs.existsSync(dest)) {
    if (!force) {
      throw new Error(`Target already exists: ${dest}\nUse --force to replace it.`);
    }
    fs.rmSync(dest, { recursive: true, force: true });
  }
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  fs.cpSync(src, dest, { recursive: true });
}

function installSkill(args) {
  const home = codexHome(args);
  const force = args.includes("--force");
  const dest = path.join(home, "skills", skillName);
  copyRecursive(skillSource, dest, force);
  console.log(`Installed Codex skill: ${dest}`);
  console.log("");
  console.log("Try it in a new Codex session with a prompt like:");
  console.log("  Use from-mbox-to-personality to analyze my Gmail MBOX into a writing persona.");
}

function runWrapper(args) {
  const sep = args.indexOf("--");
  const wrapperArgs = sep >= 0 ? args.slice(sep + 1) : args.slice(1);
  const script = path.join(skillSource, "scripts", "run_mbox_to_persona.py");
  const result = spawnSync("python", [script, ...wrapperArgs], {
    stdio: "inherit",
    cwd: repoRoot,
    env: {
      ...process.env,
      PYTHONPATH: [path.join(repoRoot, "src"), process.env.PYTHONPATH || ""].filter(Boolean).join(path.delimiter),
    },
  });
  process.exit(result.status ?? 1);
}

const args = process.argv.slice(2);
const command = args[0];

try {
  if (!command || command === "-h" || command === "--help" || command === "help") {
    usage();
  } else if (command === "install-skill") {
    installSkill(args.slice(1));
  } else if (command === "run") {
    runWrapper(args);
  } else {
    console.error(`Unknown command: ${command}`);
    usage();
    process.exit(2);
  }
} catch (error) {
  console.error(error.message);
  process.exit(1);
}

