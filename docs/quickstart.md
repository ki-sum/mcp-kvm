# Quickstart

Get `mcp-kvm` running in Claude Desktop in 3 minutes.

## 1. Install

```bash
pip install mcp-kvm[software]
```

Verify it works:

```bash
mcp-kvm --version
mcp-kvm test-screenshot
```

That last command should save `mcp-kvm-test-screenshot.jpg` in your current
directory — open it; that's what Claude will see.

## 2. Configure Claude Desktop

Open your `claude_desktop_config.json`:

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux:** `~/.config/Claude/claude_desktop_config.json`

Add an entry under `mcpServers`:

```json
{
  "mcpServers": {
    "mcp-kvm": {
      "command": "mcp-kvm-server",
      "args": [],
      "env": {
        "MCP_KVM_ADAPTER": "software"
      }
    }
  }
}
```

Or use `uvx` (no pre-install needed):

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

## 3. Restart Claude Desktop

Quit fully (Cmd+Q / Alt+F4), re-open, and check the MCP status indicator —
you should see `mcp-kvm` listed with 9 tools available.

## 4. Try it out

Ask Claude:

> *Take a screenshot and describe what you see.*

> *Open my browser and search for "kisum-gmbh.com".*

> *Type "Hello from Claude" into the currently focused window.*

## 5. Switch to remote control (BliKVM)

Once you've tested locally, point the same config at a BliKVM hardware
device to control a remote machine:

```json
{
  "mcpServers": {
    "mcp-kvm": {
      "command": "mcp-kvm-server",
      "env": {
        "MCP_KVM_ADAPTER": "blikvm",
        "BLIKVM_HOST": "192.168.1.100",
        "BLIKVM_USER": "admin",
        "BLIKVM_PASSWORD": "your-password"
      }
    }
  }
}
```

(HID mouse/keyboard support for BliKVM lands in v0.2.)
