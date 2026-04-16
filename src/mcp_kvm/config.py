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

    # KVM hardware connection (shared by BliKVM and PiKVM adapters)
    # Env vars: KVM_HOST (preferred) or BLIKVM_HOST (legacy alias)
    kvm_host: str | None
    kvm_user: str | None
    kvm_password: str | None
    kvm_verify_ssl: bool

    # Screenshot tuning
    screenshot_max_width: int
    screenshot_quality: int  # JPEG quality 1-95

    # Keyboard layout (for KVM HID paste API)
    kvm_keyboard_layout: str

    # Safety
    allow_destructive: bool  # Enable commands that could damage the system

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            adapter=os.environ.get("MCP_KVM_ADAPTER", "software").lower(),
            kvm_host=os.environ.get("KVM_HOST") or os.environ.get("BLIKVM_HOST"),
            kvm_user=os.environ.get("KVM_USER") or os.environ.get("BLIKVM_USER", "admin"),
            kvm_password=os.environ.get("KVM_PASSWORD") or os.environ.get("BLIKVM_PASSWORD"),
            kvm_verify_ssl=(os.environ.get("KVM_VERIFY_SSL") or os.environ.get("BLIKVM_VERIFY_SSL", "false")).lower() == "true",
            screenshot_max_width=int(os.environ.get("MCP_KVM_SCREENSHOT_MAX_WIDTH", "1600")),
            screenshot_quality=int(os.environ.get("MCP_KVM_SCREENSHOT_QUALITY", "75")),
            kvm_keyboard_layout=os.environ.get("MCP_KVM_KEYBOARD_LAYOUT", "en-us"),
            allow_destructive=os.environ.get("MCP_KVM_ALLOW_DESTRUCTIVE", "false").lower() == "true",
        )
