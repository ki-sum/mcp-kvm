"""KVM adapters — pluggable implementations for different hardware / software.

Each adapter implements the KVMAdapter ABC. Adapters are created via the
factory function `create_adapter()` based on the MCP_KVM_ADAPTER env var.
"""

from __future__ import annotations

from mcp_kvm.adapters.base import KVMAdapter
from mcp_kvm.config import Config


def create_adapter(config: Config) -> KVMAdapter:
    """Factory — instantiates the adapter specified in config."""
    name = config.adapter

    if name == "software":
        from mcp_kvm.adapters.software import SoftwareAdapter
        return SoftwareAdapter(config)

    if name == "blikvm":
        from mcp_kvm.adapters.blikvm import BliKVMAdapter
        return BliKVMAdapter(config)

    if name == "pikvm":
        from mcp_kvm.adapters.pikvm import PiKVMAdapter
        return PiKVMAdapter(config)

    raise ValueError(
        f"Unknown adapter '{name}'. Supported: 'software', 'blikvm', 'pikvm'. "
        f"Set MCP_KVM_ADAPTER in your MCP client env config."
    )


__all__ = ["KVMAdapter", "create_adapter"]
