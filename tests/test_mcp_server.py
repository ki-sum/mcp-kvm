"""MCP server tool tests — validates all 13 tools via direct function calls.

Mocks the adapter to avoid real hardware. Tests verify:
  - Correct adapter method is called with right arguments
  - Return format matches MCP tool contract
  - Power tools reject software adapter gracefully
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from mcp_kvm.adapters.base import KVMAdapter, Screenshot, ScreenSize


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _make_adapter(name: str = "software", power: bool = False) -> AsyncMock:
    """Create a fully mocked adapter."""
    adapter = AsyncMock(spec=KVMAdapter)
    adapter.name = name
    adapter.has_power_control = power

    fake_jpeg = b"\xff\xd8\xff\xe0" + b"\x00" * 100
    adapter.screenshot.return_value = Screenshot(
        data=fake_jpeg, mime_type="image/jpeg", width=1920, height=1080
    )
    adapter.screen_size.return_value = ScreenSize(width=1920, height=1080)
    adapter.mouse_click.return_value = None
    adapter.mouse_move.return_value = None
    adapter.mouse_scroll.return_value = None
    adapter.type_text.return_value = None
    adapter.send_key.return_value = None
    adapter.send_shortcut.return_value = None

    if power:
        adapter.power_on.return_value = None
        adapter.power_off.return_value = None
        adapter.reboot.return_value = None
        adapter.get_power_state.return_value = {
            "is_on": True, "led_power": True, "led_hdd": False,
        }

    return adapter


# ── Screenshot / Screen ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_take_screenshot():
    import mcp_kvm.server as srv

    adapter = _make_adapter()
    with patch.object(srv, "_adapter", adapter):
        result = await srv.take_screenshot()
        assert result["mime_type"] == "image/jpeg"
        assert result["width"] == 1920
        assert result["height"] == 1080
        assert "image" in result  # base64 string
        adapter.screenshot.assert_called_once()


@pytest.mark.asyncio
async def test_get_screen_size():
    import mcp_kvm.server as srv

    adapter = _make_adapter()
    with patch.object(srv, "_adapter", adapter):
        result = await srv.get_screen_size()
        assert result == {"width": 1920, "height": 1080}


# ── Mouse ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_mouse_click_default():
    import mcp_kvm.server as srv

    adapter = _make_adapter()
    with patch.object(srv, "_adapter", adapter):
        result = await srv.mouse_click(x=100, y=200)
        assert result["status"] == "ok"
        assert result["x"] == 100
        assert result["y"] == 200
        assert result["button"] == "left"
        assert result["double"] is False
        adapter.mouse_click.assert_called_once_with(100, 200, button="left", clicks=1)


@pytest.mark.asyncio
async def test_mouse_click_double_right():
    import mcp_kvm.server as srv

    adapter = _make_adapter()
    with patch.object(srv, "_adapter", adapter):
        result = await srv.mouse_click(x=50, y=50, button="right", double=True)
        assert result["button"] == "right"
        assert result["double"] is True
        adapter.mouse_click.assert_called_once_with(50, 50, button="right", clicks=2)


@pytest.mark.asyncio
async def test_mouse_move():
    import mcp_kvm.server as srv

    adapter = _make_adapter()
    with patch.object(srv, "_adapter", adapter):
        result = await srv.mouse_move(x=500, y=300)
        assert result["status"] == "ok"
        adapter.mouse_move.assert_called_once_with(500, 300)


@pytest.mark.asyncio
async def test_mouse_scroll():
    import mcp_kvm.server as srv

    adapter = _make_adapter()
    with patch.object(srv, "_adapter", adapter):
        result = await srv.mouse_scroll(x=500, y=300, amount=-3)
        assert result["amount"] == -3
        adapter.mouse_scroll.assert_called_once_with(500, 300, -3)


# ── Keyboard ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_type_text():
    import mcp_kvm.server as srv

    adapter = _make_adapter()
    with patch.object(srv, "_adapter", adapter):
        result = await srv.type_text(text="Hello World")
        assert result["status"] == "ok"
        assert result["length"] == 11
        adapter.type_text.assert_called_once_with("Hello World")


@pytest.mark.asyncio
async def test_send_key():
    import mcp_kvm.server as srv

    adapter = _make_adapter()
    with patch.object(srv, "_adapter", adapter):
        result = await srv.send_key(key="enter")
        assert result["key"] == "enter"
        adapter.send_key.assert_called_once_with("enter")


@pytest.mark.asyncio
async def test_send_shortcut():
    import mcp_kvm.server as srv

    adapter = _make_adapter()
    with patch.object(srv, "_adapter", adapter):
        result = await srv.send_shortcut(keys=["ctrl", "c"])
        assert result["keys"] == ["ctrl", "c"]
        adapter.send_shortcut.assert_called_once_with(["ctrl", "c"])


# ── Power Control ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_power_on_blikvm():
    import mcp_kvm.server as srv

    adapter = _make_adapter("blikvm", power=True)
    with patch.object(srv, "_adapter", adapter):
        result = await srv.power_on()
        assert result["status"] == "ok"
        assert result["action"] == "power_on"
        adapter.power_on.assert_called_once()


@pytest.mark.asyncio
async def test_power_off_force():
    import mcp_kvm.server as srv

    adapter = _make_adapter("blikvm", power=True)
    with patch.object(srv, "_adapter", adapter):
        result = await srv.power_off(force=True)
        assert result["status"] == "ok"
        assert result["force"] is True
        adapter.power_off.assert_called_once_with(force=True)


@pytest.mark.asyncio
async def test_reboot():
    import mcp_kvm.server as srv

    adapter = _make_adapter("blikvm", power=True)
    with patch.object(srv, "_adapter", adapter):
        result = await srv.reboot()
        assert result["status"] == "ok"
        assert result["action"] == "reboot"
        adapter.reboot.assert_called_once()


@pytest.mark.asyncio
async def test_get_power_state():
    import mcp_kvm.server as srv

    adapter = _make_adapter("blikvm", power=True)
    with patch.object(srv, "_adapter", adapter):
        result = await srv.get_power_state()
        assert result["is_on"] is True
        assert result["led_power"] is True


@pytest.mark.asyncio
async def test_power_on_software_rejects():
    """Software adapter should return error, not raise."""
    import mcp_kvm.server as srv

    adapter = _make_adapter("software", power=False)
    with patch.object(srv, "_adapter", adapter):
        result = await srv.power_on()
        assert result["status"] == "error"
        assert "does not support" in result["message"]


@pytest.mark.asyncio
async def test_power_off_software_rejects():
    import mcp_kvm.server as srv

    adapter = _make_adapter("software", power=False)
    with patch.object(srv, "_adapter", adapter):
        result = await srv.power_off()
        assert result["status"] == "error"


# ── Adapter Info ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_adapter_info_software():
    import mcp_kvm.server as srv

    adapter = _make_adapter("software", power=False)
    with patch.object(srv, "_adapter", adapter):
        result = await srv.adapter_info()
        assert result["adapter"] == "software"
        assert result["capabilities"]["power_control"] is False
        assert result["capabilities"]["bios_control"] is False


@pytest.mark.asyncio
async def test_adapter_info_blikvm():
    import mcp_kvm.server as srv

    adapter = _make_adapter("blikvm", power=True)
    with patch.object(srv, "_adapter", adapter):
        result = await srv.adapter_info()
        assert result["adapter"] == "blikvm"
        assert result["capabilities"]["power_control"] is True
        assert result["capabilities"]["bios_control"] is True
