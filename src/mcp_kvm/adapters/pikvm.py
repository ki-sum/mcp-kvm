"""PiKVM adapter — control a remote machine via PiKVM hardware.

PiKVM is the upstream project that BliKVM forked from. Key API differences:
  - Mouse coordinates: 0–32767 absolute integers (USB HID standard)
  - Authentication: HTTP Basic Auth (no JWT token)
  - Text input: POST /api/hid/print with keymap query param
  - Screenshot: GET /api/streamer/snapshot
  - Power: POST /api/atx/power with action parameter

Supported Raspberry Pi models: Pi 4, Pi Zero 2 W, Pi 3.
API Reference: https://docs.pikvm.org/api/

Required env vars:
  PIKVM_HOST       — IP or hostname of the PiKVM device
  PIKVM_USER       — HTTP Basic Auth username (default: "admin")
  PIKVM_PASSWORD   — HTTP Basic Auth password
"""

from __future__ import annotations

import asyncio
import io
import logging
from typing import Optional

from mcp_kvm.adapters.base import KVMAdapter, Screenshot, ScreenSize
from mcp_kvm.adapters.blikvm import _KEY_MAP, _MODIFIER_KEYS
from mcp_kvm.config import Config

logger = logging.getLogger("mcp_kvm.pikvm")

# PiKVM uses USB HID absolute coordinate range (0–32767)
_COORD_MAX = 32767


class PiKVMAdapter(KVMAdapter):
    """PiKVM adapter — full hardware KVM control.

    Same capabilities as BliKVM (screenshot, mouse, keyboard, ATX power)
    but with PiKVM-specific API endpoints and coordinate system.
    """

    name = "pikvm"
    has_power_control = True

    def __init__(self, config: Config):
        self.config = config
        if not config.blikvm_host:
            raise RuntimeError(
                "PiKVM adapter requires PIKVM_HOST (or BLIKVM_HOST) env var."
            )
        try:
            import httpx  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "PiKVM adapter requires httpx. "
                "Install with: pip install mcp-kvm[blikvm]"
            ) from exc

        self._host = config.blikvm_host
        self._user = config.blikvm_user or "admin"
        self._password = config.blikvm_password or ""
        self._verify = config.blikvm_verify_ssl
        proto = "https" if self._verify else "http"
        self._base_url = f"{proto}://{self._host}"
        self._client: Optional["httpx.AsyncClient"] = None
        self._screen_w: int = 0
        self._screen_h: int = 0

    async def _get_client(self):
        import httpx

        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                auth=(self._user, self._password),
                verify=self._verify,
                timeout=15.0,
            )
        return self._client

    async def _get(self, path: str, **kw):
        client = await self._get_client()
        return await client.get(path, **kw)

    async def _post(self, path: str, json_data: dict | None = None,
                    params: dict | None = None, content: bytes | None = None,
                    content_type: str | None = None):
        import httpx

        client = await self._get_client()
        headers = {}
        if content_type:
            headers["Content-Type"] = content_type
        if content is not None:
            return await client.post(path, content=content, params=params, headers=headers)
        return await client.post(path, json=json_data, params=params, headers=headers)

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    # ── Screenshot ────────────────────────────────────────────────────────

    async def screenshot(self) -> Screenshot:
        resp = await self._get("/api/streamer/snapshot")
        resp.raise_for_status()
        data = resp.content

        from PIL import Image

        img = Image.open(io.BytesIO(data))
        self._screen_w, self._screen_h = img.size

        max_w = self.config.screenshot_max_width
        if img.width > max_w:
            ratio = max_w / img.width
            img = img.resize((max_w, int(img.height * ratio)), Image.LANCZOS)

        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="JPEG", quality=self.config.screenshot_quality, optimize=True)
        return Screenshot(data=buf.getvalue(), mime_type="image/jpeg", width=img.width, height=img.height)

    async def screen_size(self) -> ScreenSize:
        if self._screen_w == 0:
            await self.screenshot()
        return ScreenSize(width=self._screen_w, height=self._screen_h)

    # ── Mouse ─────────────────────────────────────────────────────────────

    def _px_to_hid(self, px_x: int, px_y: int) -> tuple[int, int]:
        """Convert pixel coordinates to PiKVM's 0–32767 HID range."""
        if self._screen_w == 0 or self._screen_h == 0:
            sw, sh = 1920, 1080
        else:
            sw, sh = self._screen_w, self._screen_h
        hid_x = int((px_x / sw) * _COORD_MAX)
        hid_y = int((px_y / sh) * _COORD_MAX)
        return max(0, min(_COORD_MAX, hid_x)), max(0, min(_COORD_MAX, hid_y))

    async def mouse_move(self, x: int, y: int) -> None:
        hx, hy = self._px_to_hid(x, y)
        await self._post("/api/hid/events/send_mouse_move", json_data={"to": {"x": hx, "y": hy}})

    async def mouse_click(self, x: int, y: int, button: str = "left", clicks: int = 1) -> None:
        hx, hy = self._px_to_hid(x, y)
        for _ in range(clicks):
            await self._post("/api/hid/events/send_mouse_move", json_data={"to": {"x": hx, "y": hy}})
            await asyncio.sleep(0.03)
            await self._post("/api/hid/events/send_mouse_button", json_data={"button": button, "state": True})
            await self._post("/api/hid/events/send_mouse_button", json_data={"button": button, "state": False})
            await asyncio.sleep(0.03)

    async def mouse_scroll(self, x: int, y: int, amount: int) -> None:
        hx, hy = self._px_to_hid(x, y)
        await self._post("/api/hid/events/send_mouse_move", json_data={"to": {"x": hx, "y": hy}})
        await self._post("/api/hid/events/send_mouse_wheel", json_data={"delta": {"x": 0, "y": amount}})

    # ── Keyboard ──────────────────────────────────────────────────────────

    async def type_text(self, text: str) -> None:
        layout = self.config.blikvm_keyboard_layout
        await self._post(
            "/api/hid/print",
            params={"keymap": layout},
            content=text.encode("utf-8"),
            content_type="text/plain",
        )

    def _resolve_key(self, key: str) -> str:
        return _KEY_MAP.get(key.lower(), key)

    async def send_key(self, key: str) -> None:
        hid_key = self._resolve_key(key)
        await self._post("/api/hid/events/send_key", json_data={"key": hid_key, "state": True})
        await asyncio.sleep(0.02)
        await self._post("/api/hid/events/send_key", json_data={"key": hid_key, "state": False})

    async def send_shortcut(self, keys: list[str]) -> None:
        hid_keys = [self._resolve_key(k) for k in keys]
        modifiers = [k for k in hid_keys if k in _MODIFIER_KEYS]
        action_keys = [k for k in hid_keys if k not in _MODIFIER_KEYS]

        try:
            for mod in modifiers:
                await self._post("/api/hid/events/send_key", json_data={"key": mod, "state": True})
                await asyncio.sleep(0.02)
            for ak in action_keys:
                await self._post("/api/hid/events/send_key", json_data={"key": ak, "state": True})
                await asyncio.sleep(0.02)
                await self._post("/api/hid/events/send_key", json_data={"key": ak, "state": False})
            await asyncio.sleep(0.1)
        finally:
            for mod in reversed(modifiers):
                await self._post("/api/hid/events/send_key", json_data={"key": mod, "state": False})
                await asyncio.sleep(0.02)

    # ── Power Control (ATX) ───────────────────────────────────────────────

    async def power_on(self) -> None:
        await self._post("/api/atx/power", json_data={"action": "power", "wait": True})

    async def power_off(self, force: bool = False) -> None:
        action = "power_long" if force else "power"
        await self._post("/api/atx/power", json_data={"action": action, "wait": True})

    async def reboot(self) -> None:
        await self._post("/api/atx/power", json_data={"action": "reset", "wait": True})

    async def get_power_state(self) -> dict:
        try:
            resp = await self._get("/api/atx")
            result = resp.json().get("result", {})
            leds = result.get("leds", {})
            return {
                "is_on": leds.get("power", False),
                "led_power": leds.get("power", False),
                "led_hdd": leds.get("hdd", False),
            }
        except Exception as e:
            logger.warning("Failed to get power state: %s", e)
            return {"is_on": False, "led_power": False, "led_hdd": False}
