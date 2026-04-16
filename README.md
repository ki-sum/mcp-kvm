# mcp-kvm

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-green.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-Compatible-purple.svg)](https://modelcontextprotocol.io/)

**The only AI that can fix a crashed computer, not just use one.**

An MCP (Model Context Protocol) server that lets Claude, Cursor, or any
MCP-compatible AI client **control any computer through KVM hardware** —
including BIOS/UEFI, remote power on/off, login screens, blue screens, and locked machines.
When Anthropic's Computer Use or OpenAI's Operator hit a locked screen and
give up, `mcp-kvm` keeps working.

> **Status:** Alpha (v0.1) — software, BliKVM, and PiKVM adapters all functional.
> 13 MCP tools including screenshot, mouse, keyboard, and ATX power control.

---

## Why KVM instead of a software agent?

| Scenario | Software agents | `mcp-kvm` |
|----------|----------------|-----------|
| Automate a logged-in desktop | ✅ | ✅ |
| Log in to a locked machine | ❌ | ✅ |
| Fix a blue screen or boot loop | ❌ | ✅ |
| Control BIOS / UEFI settings | ❌ | ✅ |
| Power on / power off remotely | ❌ | ✅ |
| **Zero software on target** — nothing to install | ❌ | ✅ |
| **IT-restricted machines** — admin blocks all installs | ❌ | ✅ |
| Industrial / POS / embedded / legacy systems | ❌ | ✅ |
| Air-gapped / compliance-restricted environments | ❌ | ✅ |

**Zero intrusion.** KVM hardware sits between your keyboard/mouse/monitor and
the target computer. The target sees it as a normal USB keyboard and mouse —
no agent, no driver, no software, no admin rights needed. IT departments can't
block it because there's nothing to install.

---

## Quick Start

### 1. Install

```bash
# Easiest — one-line setup (auto-installs Python package, writes MCP config)
npx mcp-kvm init

# Or install Python package directly
pip install mcp-kvm[software]      # for controlling this machine
pip install mcp-kvm[blikvm]        # for BliKVM hardware
pip install mcp-kvm[pikvm]         # for PiKVM hardware
pip install mcp-kvm[all]           # all adapters
```

### 2. Configure your MCP client

After `npx mcp-kvm init`, a `.mcp.json` is written to your current directory
(for Claude Code / Cursor). For **Claude Desktop**, add to
`claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mcp-kvm": {
      "command": "uvx",
      "args": ["mcp-kvm-server"],
      "env": {
        "MCP_KVM_ADAPTER": "software"
      }
    }
  }
}
```

### 3. Restart your AI client and ask

> *"Take a screenshot and tell me what's on my screen."*

> *"Open the Start menu and launch Notepad, then type 'Hello from Claude'."*

The AI now has 13 tools: `take_screenshot`, `get_screen_size`, `mouse_click`,
`mouse_move`, `mouse_scroll`, `type_text`, `send_key`, `send_shortcut`,
`power_on`, `power_off`, `reboot`, `get_power_state`, `adapter_info`.

---

## Adapters

`mcp-kvm` is adapter-based — the same MCP tools work across different
backends. Set `MCP_KVM_ADAPTER` in your client config to switch.

### `software` (default)

Uses `pyautogui` to control the same machine the server runs on. Good for:
- Quick local testing
- Single-machine automation
- Running on a Pi/NAS with an attached display

```json
"env": { "MCP_KVM_ADAPTER": "software" }
```

### `blikvm` (hardware)

Controls a remote machine via [BliKVM v4](https://blikvm.com/). Full support:
screenshot, mouse, keyboard, ATX power on/off/reboot.

```json
"env": {
  "MCP_KVM_ADAPTER": "blikvm",
  "KVM_HOST": "192.168.1.100",
  "KVM_USER": "admin",
  "KVM_PASSWORD": "..."
}
```

### `pikvm` (hardware, community-tested)

Controls a remote machine via [PiKVM](https://pikvm.org/). Implements full
API support based on official PiKVM documentation. **Not yet verified on real
hardware** — community testing and feedback welcome via
[GitHub Issues](https://github.com/ki-sum/mcp-kvm/issues).

```json
"env": {
  "MCP_KVM_ADAPTER": "pikvm",
  "KVM_HOST": "192.168.1.100",
  "KVM_USER": "admin",
  "KVM_PASSWORD": "..."
}
```

### Write your own

Subclass `mcp_kvm.adapters.base.KVMAdapter` and register via entry points.
See [docs/adapters/custom.md](docs/adapters/custom.md).

---

## Remote Access (from outside your LAN)

`mcp-kvm` connects directly to your KVM device on the local network. To
control machines **while traveling**, you need a way to reach your home/office
network. The recommended approach is a mesh VPN — no port forwarding, no
cloud relay, end-to-end encrypted.

### Tailscale (recommended — 5 minutes to set up)

1. Install [Tailscale](https://tailscale.com/) on your laptop/phone **and** on
   the machine running `mcp-kvm-server` (or on the KVM device itself if it
   supports it — PiKVM has a Tailscale plugin).
2. Both devices join the same Tailnet.
3. Use the Tailscale IP in your MCP config:

```json
"env": {
  "MCP_KVM_ADAPTER": "blikvm",
  "KVM_HOST": "100.64.0.5"
}
```

Now Claude Desktop on your laptop can reach the BliKVM at home, anywhere in
the world. Tailscale's free tier supports up to 100 devices.

### Other VPN options

| Option | Complexity | Notes |
|--------|-----------|-------|
| **Tailscale** | Easy | Free, peer-to-peer, recommended |
| **ZeroTier** | Easy | Similar to Tailscale, self-hostable |
| **WireGuard** | Medium | Manual config, fastest raw performance |
| **Cloudflare Tunnel** | Medium | Good if you already use Cloudflare |
| SSH tunnel | Advanced | `ssh -L 8080:blikvm:80 your-server` |

> **Tip:** Most homelab and sysadmin users already run Tailscale or
> WireGuard — `mcp-kvm` slots right into your existing setup.

---

## Security

- `mcp-kvm` runs **entirely on your machine** — no cloud, no data upload.
- Screenshots and inputs never leave the MCP protocol stream to your AI client.
- The `software` adapter **intentionally disables pyautogui's failsafe** so
  the AI can operate freely. Set `MCP_KVM_ALLOW_DESTRUCTIVE=false` (default)
  to prevent the most dangerous shortcuts.
- You control the AI. Treat MCP tools like any remote-execution capability
  and review what your AI is about to do before confirming.

---

## Project relationship

`mcp-kvm` is the open-source core of the [KiSum Bot](https://bot.ki-sum.ai)
project — a commercial AI worker platform for sysadmins and automation teams.
The MCP server is **Apache 2.0**; premium enterprise features (Lexoffice /
DATEV skills, team collaboration, audit logs) live in the private
[kisum platform](https://bot.ki-sum.ai).

If you like `mcp-kvm`, please star it and share your use case on
[GitHub Discussions](https://github.com/ki-sum/mcp-kvm/discussions).

---

## Roadmap

- [x] **v0.1** — Software, BliKVM, PiKVM adapters, 13 tools, npm + PyPI packaging
- [ ] **v0.2** — Multi-display support, image-based click verification
- [ ] **v0.3** — MCP Resources for knowledge injection (browser patterns, keyboard shortcuts)
- [ ] **v0.4** — Context memory + action verification (AI remembers past actions, verifies success)
- [ ] **v0.5** — `run_task` tool (built-in agent loop with self-healing and precision clicking)
- [ ] **v1.0** — Stable API, entry-point adapter plugins, certified adapter list

---

## Contributing

We actively welcome new KVM adapters, bug reports, and documentation
improvements. See [CONTRIBUTING.md](CONTRIBUTING.md) (coming soon).

---

## License

Apache 2.0 — see [LICENSE](LICENSE).

Copyright 2026 ki-sum
