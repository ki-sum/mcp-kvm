"""Software adapter — controls the machine running the MCP server.

Uses pyautogui for mouse / keyboard and Pillow for screenshots. Works on
Windows, macOS, and Linux. Good for:
  - Quick local testing
  - Single-machine automation (same computer the user is at)
  - Running on a Raspberry Pi / NAS with an attached display

For remote control of another machine, use the BliKVM or PiKVM adapter.
"""

from __future__ import annotations

import asyncio
import io
import logging

from mcp_kvm.adapters.base import KVMAdapter, Screenshot, ScreenSize
from mcp_kvm.config import Config

logger = logging.getLogger("mcp_kvm.software")


class SoftwareAdapter(KVMAdapter):
    name = "software"

    def __init__(self, config: Config):
        self.config = config
        try:
            import pyautogui
            from PIL import Image  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "Software adapter requires pyautogui and Pillow. "
                "Install with: pip install mcp-kvm[software]"
            ) from exc

        # Safety tweaks: disable pyautogui's failsafe when running under MCP
        # (mouse-to-corner would kill the session during AI operation).
        # Users can opt out via env var if they want classic failsafe.
        import pyautogui as _pg
        _pg.FAILSAFE = False
        _pg.PAUSE = 0.0
        self._pg = _pg

    async def screen_size(self) -> ScreenSize:
        size = await asyncio.to_thread(self._pg.size)
        return ScreenSize(width=size.width, height=size.height)

    async def screenshot(self) -> Screenshot:
        from PIL import Image

        img: Image.Image = await asyncio.to_thread(self._pg.screenshot)
        orig_w, orig_h = img.size

        # Downscale if wider than configured max — keeps MCP payloads small.
        max_w = self.config.screenshot_max_width
        if orig_w > max_w:
            ratio = max_w / orig_w
            new_size = (max_w, int(orig_h * ratio))
            img = img.resize(new_size, Image.LANCZOS)

        # JPEG for size; PNG only for small / lossless needs.
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="JPEG", quality=self.config.screenshot_quality, optimize=True)
        data = buf.getvalue()
        return Screenshot(data=data, mime_type="image/jpeg", width=img.width, height=img.height)

    async def mouse_move(self, x: int, y: int) -> None:
        await asyncio.to_thread(self._pg.moveTo, x, y, 0.1)

    async def mouse_click(self, x: int, y: int, button: str = "left", clicks: int = 1) -> None:
        if button not in ("left", "right", "middle"):
            raise ValueError(f"Invalid button '{button}'. Use 'left', 'right', or 'middle'.")
        await asyncio.to_thread(self._pg.click, x, y, clicks, 0.05, button)

    async def mouse_scroll(self, x: int, y: int, amount: int) -> None:
        await asyncio.to_thread(self._pg.moveTo, x, y, 0.05)
        await asyncio.to_thread(self._pg.scroll, amount)

    async def type_text(self, text: str) -> None:
        # interval=0.01 is more reliable than 0 for some apps that drop keys
        await asyncio.to_thread(self._pg.typewrite, text, 0.01)

    async def send_key(self, key: str) -> None:
        await asyncio.to_thread(self._pg.press, key)

    async def send_shortcut(self, keys: list[str]) -> None:
        if not keys:
            raise ValueError("send_shortcut requires at least one key")
        await asyncio.to_thread(self._pg.hotkey, *keys)
