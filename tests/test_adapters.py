"""Basic adapter unit tests — no real hardware required."""

from __future__ import annotations

import pytest

from mcp_kvm.adapters.base import KVMAdapter, Screenshot, ScreenSize
from mcp_kvm.config import Config


def test_screen_size_dataclass():
    size = ScreenSize(width=1920, height=1080)
    assert size.width == 1920
    assert size.height == 1080


def test_screenshot_dataclass():
    shot = Screenshot(data=b"\x00\x01", mime_type="image/jpeg", width=640, height=480)
    assert shot.data == b"\x00\x01"
    assert shot.mime_type == "image/jpeg"


def test_base_is_abstract():
    with pytest.raises(TypeError):
        KVMAdapter()  # type: ignore[abstract]


def test_config_from_env(monkeypatch):
    monkeypatch.setenv("MCP_KVM_ADAPTER", "blikvm")
    monkeypatch.setenv("KVM_HOST", "10.0.0.1")
    monkeypatch.setenv("MCP_KVM_SCREENSHOT_QUALITY", "90")

    cfg = Config.from_env()
    assert cfg.adapter == "blikvm"
    assert cfg.kvm_host == "10.0.0.1"
    assert cfg.screenshot_quality == 90


def test_config_legacy_env_alias(monkeypatch):
    """BLIKVM_HOST should still work as a legacy alias for KVM_HOST."""
    monkeypatch.delenv("KVM_HOST", raising=False)
    monkeypatch.setenv("BLIKVM_HOST", "10.0.0.2")

    cfg = Config.from_env()
    assert cfg.kvm_host == "10.0.0.2"


def test_config_defaults(monkeypatch):
    for key in ("MCP_KVM_ADAPTER", "KVM_HOST", "BLIKVM_HOST"):
        monkeypatch.delenv(key, raising=False)

    cfg = Config.from_env()
    assert cfg.adapter == "software"
    assert cfg.kvm_host is None
    assert cfg.allow_destructive is False


def test_unknown_adapter_raises():
    from mcp_kvm.adapters import create_adapter

    cfg = Config(
        adapter="nonexistent",
        kvm_host=None,
        kvm_user=None,
        kvm_password=None,
        kvm_verify_ssl=False,
        screenshot_max_width=1600,
        screenshot_quality=75,
        kvm_keyboard_layout="en-us",
        allow_destructive=False,
    )
    with pytest.raises(ValueError, match="Unknown adapter"):
        create_adapter(cfg)
