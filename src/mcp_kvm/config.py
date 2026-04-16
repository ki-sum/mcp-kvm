"""Configuration loaded from environment variables.

MCP servers are configured via the `env` field in the MCP client config
(e.g. Claude Desktop's claude_desktop_config.json). We read all settings
from environment variables with sensible defaults.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Config:
    """Runtime configuration for the MCP server."""

    adapter: str  # "software" | "blikvm" | "pikvm"

    # BliKVM / PiKVM
    blikvm_host: str | None
    blikvm_user: str | None
    blikvm_password: str | None
    blikvm_verify_ssl: bool

    # Screenshot tuning
    screenshot_max_width: int
    screenshot_quality: int  # JPEG quality 1-95

    # Keyboard layout (for BliKVM/PiKVM HID paste)
    blikvm_keyboard_layout: str

    # Safety
    allow_destructive: bool  # Enable commands that could damage the system

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            adapter=os.environ.get("MCP_KVM_ADAPTER", "software").lower(),
            blikvm_host=os.environ.get("BLIKVM_HOST"),
            blikvm_user=os.environ.get("BLIKVM_USER", "admin"),
            blikvm_password=os.environ.get("BLIKVM_PASSWORD"),
            blikvm_verify_ssl=os.environ.get("BLIKVM_VERIFY_SSL", "false").lower() == "true",
            screenshot_max_width=int(os.environ.get("MCP_KVM_SCREENSHOT_MAX_WIDTH", "1600")),
            screenshot_quality=int(os.environ.get("MCP_KVM_SCREENSHOT_QUALITY", "75")),
            blikvm_keyboard_layout=os.environ.get("MCP_KVM_KEYBOARD_LAYOUT", "en-us"),
            allow_destructive=os.environ.get("MCP_KVM_ALLOW_DESTRUCTIVE", "false").lower() == "true",
        )
