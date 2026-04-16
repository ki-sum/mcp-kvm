"""mcp-kvm — MCP server entry point.

Exposes a set of tools that any MCP client (Claude Desktop, Claude Code,
Cursor, etc.) can call to control a computer through the configured KVM
adapter (software / BliKVM / PiKVM / ...).
"""

from __future__ import annotations

import base64
import logging
import sys

from mcp.server.fastmcp import FastMCP

from mcp_kvm import __version__
from mcp_kvm.adapters import create_adapter
from mcp_kvm.config import Config

logger = logging.getLogger("mcp_kvm")
logging.basicConfig(
    level=logging.INFO,
    format="%(name)s %(levelname)s: %(message)s",
    stream=sys.stderr,
)

# Single config + adapter loaded at startup.
_config = Config.from_env()
_adapter = create_adapter(_config)

mcp = FastMCP("mcp-kvm")


# ── Tools ────────────────────────────────────────────────────────────────────


@mcp.tool()
async def take_screenshot() -> dict:
    """Capture the current screen of the target computer.

    Returns an image the AI can view directly. Use this before any other
    action to see what is on screen.

    Returns:
        Object with:
          - image: base64-encoded JPEG data
          - mime_type: always "image/jpeg"
          - width, height: image dimensions in pixels
    """
    shot = await _adapter.screenshot()
    return {
        "image": base64.b64encode(shot.data).decode("ascii"),
        "mime_type": shot.mime_type,
        "width": shot.width,
        "height": shot.height,
    }


@mcp.tool()
async def get_screen_size() -> dict:
    """Return the resolution of the target screen.

    Use this to interpret pixel coordinates returned by take_screenshot().
    """
    size = await _adapter.screen_size()
    return {"width": size.width, "height": size.height}


@mcp.tool()
async def mouse_click(x: int, y: int, button: str = "left", double: bool = False) -> dict:
    """Click at pixel coordinates (x, y).

    Args:
        x: Horizontal pixel position (0 = left edge).
        y: Vertical pixel position (0 = top edge).
        button: "left" (default), "right", or "middle".
        double: True for double-click, False for single click.

    Returns:
        Status dict confirming the click.
    """
    clicks = 2 if double else 1
    await _adapter.mouse_click(x, y, button=button, clicks=clicks)
    return {"status": "ok", "action": "click", "x": x, "y": y, "button": button, "double": double}


@mcp.tool()
async def mouse_move(x: int, y: int) -> dict:
    """Move the mouse cursor to (x, y) without clicking.

    Useful for hovering over menus or verifying cursor position before a click.
    """
    await _adapter.mouse_move(x, y)
    return {"status": "ok", "action": "move", "x": x, "y": y}


@mcp.tool()
async def mouse_scroll(x: int, y: int, amount: int) -> dict:
    """Scroll at position (x, y).

    Args:
        x, y: Position where scrolling happens.
        amount: Positive = scroll up, negative = scroll down. Typical range -10..10.
    """
    await _adapter.mouse_scroll(x, y, amount)
    return {"status": "ok", "action": "scroll", "x": x, "y": y, "amount": amount}


@mcp.tool()
async def type_text(text: str) -> dict:
    """Type a string of text at the current focus.

    For special keys (Enter, Tab, etc.) use send_key instead.
    """
    await _adapter.type_text(text)
    return {"status": "ok", "action": "type", "length": len(text)}


@mcp.tool()
async def send_key(key: str) -> dict:
    """Press a single key (e.g. 'enter', 'tab', 'escape', 'f1', 'backspace').

    For key combinations use send_shortcut.
    """
    await _adapter.send_key(key)
    return {"status": "ok", "action": "key", "key": key}


@mcp.tool()
async def send_shortcut(keys: list[str]) -> dict:
    """Send a keyboard shortcut (e.g. ['ctrl', 'c'] for copy).

    Args:
        keys: List of keys to press simultaneously (modifiers first).

    Examples:
        ['ctrl', 'c']      → copy
        ['ctrl', 'v']      → paste
        ['alt', 'tab']     → switch window
        ['ctrl', 'alt', 'delete']  → security screen (BIOS/KVM only)
    """
    await _adapter.send_shortcut(keys)
    return {"status": "ok", "action": "shortcut", "keys": keys}


@mcp.tool()
async def power_on() -> dict:
    """Turn on the target machine by pressing the physical power button.

    Requires a hardware KVM adapter (BliKVM, PiKVM) with ATX power control.
    Does NOT work with the software adapter.
    """
    if not _adapter.has_power_control:
        return {"status": "error", "message": f"{_adapter.name} adapter does not support power control. Use a hardware KVM."}
    await _adapter.power_on()
    return {"status": "ok", "action": "power_on"}


@mcp.tool()
async def power_off(force: bool = False) -> dict:
    """Turn off the target machine.

    Args:
        force: False = short press (graceful shutdown). True = long press (force off, like holding the power button for 5 seconds).
    """
    if not _adapter.has_power_control:
        return {"status": "error", "message": f"{_adapter.name} adapter does not support power control."}
    await _adapter.power_off(force=force)
    return {"status": "ok", "action": "power_off", "force": force}


@mcp.tool()
async def reboot() -> dict:
    """Press the hardware reset button on the target machine.

    This is a hard reboot — equivalent to pressing the physical reset button.
    Requires a hardware KVM adapter with ATX control.
    """
    if not _adapter.has_power_control:
        return {"status": "error", "message": f"{_adapter.name} adapter does not support power control."}
    await _adapter.reboot()
    return {"status": "ok", "action": "reboot"}


@mcp.tool()
async def get_power_state() -> dict:
    """Check if the target machine is powered on or off.

    Reads the ATX power LED state from the KVM hardware.
    Returns is_on (bool), led_power (bool), led_hdd (bool).
    """
    if not _adapter.has_power_control:
        return {"status": "error", "message": f"{_adapter.name} adapter does not support power control."}
    state = await _adapter.get_power_state()
    return {"status": "ok", **state}


@mcp.tool()
async def adapter_info() -> dict:
    """Return information about the currently active KVM adapter.

    Useful for the AI to know what the target environment is capable of
    (e.g. BliKVM can send Ctrl+Alt+Del to a BIOS screen, pyautogui cannot).
    """
    return {
        "adapter": _adapter.name,
        "version": __version__,
        "capabilities": {
            "bios_control": _adapter.name in ("blikvm", "pikvm"),
            "pre_login_control": _adapter.name in ("blikvm", "pikvm"),
            "crash_recovery": _adapter.name in ("blikvm", "pikvm"),
            "power_control": _adapter.has_power_control,
        },
    }


# ── Entry points ─────────────────────────────────────────────────────────────


def main() -> None:
    """Start the MCP server on stdio."""
    logger.info(
        "mcp-kvm v%s starting — adapter=%s", __version__, _adapter.name
    )
    mcp.run()


if __name__ == "__main__":
    main()
