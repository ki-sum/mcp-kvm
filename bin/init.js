#!/usr/bin/env node
// npx mcp-kvm init — one-line MCP setup for mcp-kvm

const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");

const MCP_CONFIG_FILE = ".mcp.json";

// ANSI color helpers
const green = (s) => `\x1b[32m${s}\x1b[0m`;
const cyan = (s) => `\x1b[36m${s}\x1b[0m`;
const bold = (s) => `\x1b[1m${s}\x1b[0m`;
const dim = (s) => `\x1b[2m${s}\x1b[0m`;
const yellow = (s) => `\x1b[33m${s}\x1b[0m`;
const red = (s) => `\x1b[31m${s}\x1b[0m`;

/**
 * Detect the correct python command ("python" or "python3").
 */
function detectPythonCommand() {
  for (const cmd of ["python", "python3"]) {
    try {
      execSync(`${cmd} --version`, { stdio: "ignore", timeout: 3000 });
      return cmd;
    } catch {}
  }
  return "python";
}

/**
 * Detect the best way to run the MCP server.
 * Priority: uvx > pip-installed > python -m
 */
function detectServerConfig() {
  const pythonCmd = detectPythonCommand();

  // Option 1: uvx (best — auto-downloads, no pre-install needed)
  try {
    execSync("uvx --version", { stdio: "ignore" });
    return {
      command: "uvx",
      args: ["mcp-kvm-server"],
      method: "uvx",
    };
  } catch {}

  // Option 2: pip-installed (mcp-kvm-server in PATH)
  try {
    execSync("mcp-kvm-server --help", { stdio: "ignore", timeout: 3000 });
    return {
      command: "mcp-kvm-server",
      args: [],
      method: "pip",
    };
  } catch {}

  // Option 3: python -m (if package installed but script not on PATH)
  try {
    execSync("pip show mcp-kvm", { stdio: "ignore", timeout: 3000 });
    return {
      command: pythonCmd,
      args: ["-m", "mcp_kvm.server"],
      method: `${pythonCmd} -m`,
    };
  } catch {}

  // Fallback: auto-install and use
  try {
    console.log(`${dim("Installing mcp-kvm via pip...")}`);
    execSync("pip install mcp-kvm[software]", { stdio: "inherit", timeout: 120000 });
    try {
      execSync("mcp-kvm-server --help", { stdio: "ignore", timeout: 3000 });
      return {
        command: "mcp-kvm-server",
        args: [],
        method: "pip (auto-installed)",
      };
    } catch {}
    return {
      command: pythonCmd,
      args: ["-m", "mcp_kvm.server"],
      method: "pip (auto-installed)",
    };
  } catch {}

  console.error(
    `${red("Error:")} Could not find or install mcp-kvm.\n` +
    `Please install manually: ${cyan("pip install mcp-kvm[software]")}\n` +
    `Then re-run: ${cyan("npx mcp-kvm init")}`
  );
  process.exit(1);
}

function printHelp() {
  console.log(`
${bold("mcp-kvm")} — AI control for any computer via KVM hardware

${bold("Usage:")}
  npx mcp-kvm init         Set up MCP server in current project (.mcp.json)
  npx mcp-kvm init --desktop  Set up in Claude Desktop config

${bold("Install methods:")}
  pip install mcp-kvm[software]   Software mode (control this machine)
  pip install mcp-kvm[blikvm]     BliKVM hardware adapter
  pip install mcp-kvm[all]        All adapters
  uvx mcp-kvm-server              Run via uvx (no install needed)

${bold("Adapters:")}
  software  Control the machine running the MCP server (pyautogui)
  blikvm    Control a remote machine via BliKVM hardware
  pikvm     Control a remote machine via PiKVM hardware

${dim("Docs: https://github.com/ki-sum/mcp-kvm")}
`);
}

function getClaudeDesktopConfigPath() {
  const home = process.env.HOME || process.env.USERPROFILE;
  if (process.platform === "darwin") {
    return path.join(home, "Library", "Application Support", "Claude", "claude_desktop_config.json");
  }
  if (process.platform === "win32") {
    return path.join(process.env.APPDATA || "", "Claude", "claude_desktop_config.json");
  }
  // Linux
  return path.join(home, ".config", "Claude", "claude_desktop_config.json");
}

function main() {
  const args = process.argv.slice(2);

  if (args[0] !== "init") {
    printHelp();
    process.exit(0);
  }

  const useDesktop = args.includes("--desktop");
  const configPath = useDesktop
    ? getClaudeDesktopConfigPath()
    : path.join(process.cwd(), MCP_CONFIG_FILE);

  let config = { mcpServers: {} };
  let existed = false;

  if (fs.existsSync(configPath)) {
    existed = true;
    try {
      const raw = fs.readFileSync(configPath, "utf-8");
      config = JSON.parse(raw);
      if (!config.mcpServers) config.mcpServers = {};
    } catch (err) {
      console.error(`${red("Error:")} Could not parse ${configPath}: ${err.message}`);
      process.exit(1);
    }
  }

  if (config.mcpServers["mcp-kvm"]) {
    console.log(`
${green("\u2713")} mcp-kvm is already configured in ${cyan(configPath)}

${bold("Next steps:")}
  1. Restart your AI client (Claude Desktop, Claude Code, Cursor, etc.)
  2. Ask your AI: ${cyan('"Take a screenshot of my screen"')}

${dim("Adapter is configured via env vars — see docs for details.")}
`);
    process.exit(0);
  }

  const serverConfig = detectServerConfig();

  const entry = {
    command: serverConfig.command,
    args: serverConfig.args,
    env: {
      MCP_KVM_ADAPTER: "software",
    },
  };

  config.mcpServers["mcp-kvm"] = entry;

  // Ensure parent directory exists
  const dir = path.dirname(configPath);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }

  fs.writeFileSync(configPath, JSON.stringify(config, null, 2) + "\n");

  console.log(`
${green("\u2713")} mcp-kvm configured ${existed ? "(updated)" : "(created)"} at ${cyan(configPath)}

${bold("Server launch method:")} ${yellow(serverConfig.method)}

${bold("Default adapter:")} software (controls this machine via pyautogui)

${bold("To switch adapters,")} edit ${cyan(configPath)} and set:
  ${dim('"env": { "MCP_KVM_ADAPTER": "blikvm", "BLIKVM_HOST": "..." }')}

${bold("Next steps:")}
  1. Restart your AI client (Claude Desktop, Claude Code, Cursor, etc.)
  2. Ask your AI: ${cyan('"Take a screenshot of my screen"')}

${dim("Docs: https://github.com/ki-sum/mcp-kvm")}
`);
}

main();
