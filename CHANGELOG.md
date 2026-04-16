# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — 2026-04-15

### Added
- Initial alpha release.
- MCP server exposing 13 tools: `take_screenshot`, `get_screen_size`,
  `mouse_click`, `mouse_move`, `mouse_scroll`, `type_text`, `send_key`,
  `send_shortcut`, `power_on`, `power_off`, `reboot`, `get_power_state`,
  `adapter_info`.
- `software` adapter (pyautogui) — controls the local machine on
  Windows / macOS / Linux.
- `blikvm` adapter — full support: screenshot, mouse, keyboard, ATX power.
  Tested on BliKVM v4 hardware.
- `pikvm` adapter — full API support based on PiKVM documentation.
  Community testing welcome (not yet verified on real hardware).
- `npx mcp-kvm init` — one-line MCP config generation.
- `pip install mcp-kvm[software]` / `[blikvm]` / `[pikvm]` / `[all]`.
- Remote Access guide (Tailscale, WireGuard, ZeroTier).
