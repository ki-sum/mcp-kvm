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
    monkeypatch.setenv("BLIKVM_HOST", "10.0.0.1")
    monkeypatch.setenv("MCP_KVM_SCREENSHOT_QUALITY", "90")

    cfg = Config.from_env()
    assert cfg.adapter == "blikvm"
    assert cfg.blikvm_host == "10.0.0.1"
    assert cfg.screenshot_quality == 90


def test_config_defaults(monkeypatch):
    # Clear any leaked env vars from a prior test
    for key in ("MCP_KVM_ADAPTER", "BLIKVM_HOST"):
        monkeypatch.delenv(key, raising=False)

    cfg = Config.from_env()
    assert cfg.adapter == "software"
    assert cfg.blikvm_host is None
    assert cfg.allow_destructive is False


def test_unknown_adapter_raises():
    from mcp_kvm.adapters import create_adapter

    cfg = Config(
        adapter="nonexistent",
        blikvm_host=None,
        blikvm_user=None,
        blikvm_password=None,
        blikvm_verify_ssl=False,
        screenshot_max_width=1600,
        screenshot_quality=75,
        blikvm_keyboard_layout="en-us",
        allow_destructive=False,
    )
    with pytest.raises(ValueError, match="Unknown adapter"):
        create_adapter(cfg)
