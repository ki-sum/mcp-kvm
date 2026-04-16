"""BliKVM adapter — control a remote machine via BliKVM v4 hardware.

Full implementation: screenshot, mouse, keyboard, and ATX power control.
Communicates with BliKVM via its REST API over HTTP(S).

BliKVM uses relative coordinates (0.0–1.0) for mouse position and HID key
codes for keyboard input. The adapter translates pixel coordinates and
human-readable key names into the hardware protocol.

Required env vars:
  BLIKVM_HOST       — IP or hostname of the BliKVM device
  BLIKVM_USER       — HTTP Basic Auth username (default: "admin")
  BLIKVM_PASSWORD   — HTTP Basic Auth password
"""

from __future__ import annotations

import asyncio
import base64
import io
import logging
import time
from typing import Optional

from mcp_kvm.adapters.base import KVMAdapter, Screenshot, ScreenSize
from mcp_kvm.config import Config

logger = logging.getLogger("mcp_kvm.blikvm")

# Map human-readable key names → BliKVM HID key codes
_KEY_MAP: dict[str, str] = {
    # Letters
    **{chr(c): f"Key{chr(c).upper()}" for c in range(ord("a"), ord("z") + 1)},
    # Digits
    **{str(d): f"Digit{d}" for d in range(10)},
    # Function keys
    **{f"f{n}": f"F{n}" for n in range(1, 13)},
    # Common keys
    "enter": "Enter", "return": "Enter",
    "tab": "Tab",
    "space": "Space",
    "backspace": "Backspace",
    "delete": "Delete",
    "escape": "Escape", "esc": "Escape",
    "up": "ArrowUp", "down": "ArrowDown",
    "left": "ArrowLeft", "right": "ArrowRight",
    "home": "Home", "end": "End",
    "pageup": "PageUp", "pagedown": "PageDown",
    "insert": "Insert",
    "capslock": "CapsLock",
    "numlock": "NumLock",
    "printscreen": "PrintScreen",
    "scrolllock": "ScrollLock",
    "pause": "Pause",
    # Modifiers
    "ctrl": "ControlLeft", "control": "ControlLeft",
    "shift": "ShiftLeft",
    "alt": "AltLeft",
    "meta": "MetaLeft", "win": "MetaLeft", "super": "MetaLeft", "cmd": "MetaLeft",
    # Punctuation (US layout)
    "-": "Minus", "=": "Equal",
    "[": "BracketLeft", "]": "BracketRight",
    "\\": "Backslash", ";": "Semicolon",
    "'": "Quote", "`": "Backquote",
    ",": "Comma", ".": "Period",
    "/": "Slash",
}

_MODIFIER_KEYS = {
    "ControlLeft", "ControlRight", "ShiftLeft", "ShiftRight",
    "AltLeft", "AltRight", "MetaLeft", "MetaRight",
}


class BliKVMAdapter(KVMAdapter):
    """BliKVM v4 adapter — full hardware KVM control.

    Capabilities:
      - Screenshot capture (JPEG from /api/video/screenshot)
      - Mouse control (absolute coordinates via /api/mouse/event)
      - Keyboard: type text (/api/hid/paste), single keys, shortcuts
      - ATX power control: power on, power off, force off, reboot, state query
      - Works at BIOS level, login screens, crash recovery
    """

    name = "blikvm"
    has_power_control = True

    def __init__(self, config: Config):
        self.config = config
        if not config.kvm_host:
            raise RuntimeError(
                "BliKVM adapter requires BLIKVM_HOST env var. "
                "Set it in your MCP client config."
            )
        try:
            import httpx  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "BliKVM adapter requires httpx. "
                "Install with: pip install mcp-kvm[blikvm]"
            ) from exc

        self._host = config.kvm_host
        self._user = config.kvm_user or "admin"
        self._password = config.kvm_password or ""
        self._verify = config.kvm_verify_ssl
        proto = "https" if self._verify else "http"
        self._base_url = f"{proto}://{self._host}"
        self._client: Optional["httpx.AsyncClient"] = None
        self._token: Optional[str] = None
        # Cache screen size (queried once, reused)
        self._screen_w: int = 0
        self._screen_h: int = 0

    async def _get_client(self):
        import httpx

        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                verify=self._verify,
                timeout=15.0,
            )
            # Authenticate to get token
            await self._login()
        return self._client

    async def _login(self) -> None:
        """Authenticate with BliKVM and obtain a session token."""
        import httpx

        client = self._client
        if client is None:
            return
        try:
            resp = await client.post(
                "/api/login",
                json={"username": self._user, "password": self._password},
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") == 0:
                self._token = data.get("data", {}).get("token")
                logger.info("BliKVM authenticated successfully")
            else:
                logger.warning("BliKVM login failed: %s", data.get("msg"))
        except httpx.HTTPError as e:
            logger.error("BliKVM login error: %s", e)

    def _headers(self) -> dict[str, str]:
        """Build request headers with auth."""
        h: dict[str, str] = {"Content-Type": "application/json"}
        if self._token:
            h["Authorization"] = f"Bearer {self._token}"
        else:
            cred = base64.b64encode(f"{self._user}:{self._password}".encode()).decode()
            h["Authorization"] = f"Basic {cred}"
        return h

    async def _get(self, path: str, **kw):
        client = await self._get_client()
        return await client.get(path, headers=self._headers(), **kw)

    async def _post(self, path: str, json_data: dict | None = None, params: dict | None = None):
        client = await self._get_client()
        return await client.post(path, headers=self._headers(), json=json_data, params=params)

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    # ── Screenshot ────────────────────────────────────────────────────────

    async def screenshot(self) -> Screenshot:
        resp = await self._get("/api/video/screenshot")
        resp.raise_for_status()
        data = resp.content

        from PIL import Image

        img = Image.open(io.BytesIO(data))
        self._screen_w, self._screen_h = img.size

        # Downscale if needed
        max_w = self.config.screenshot_max_width
        if img.width > max_w:
            ratio = max_w / img.width
            img = img.resize((max_w, int(img.height * ratio)), Image.LANCZOS)

        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="JPEG", quality=self.config.screenshot_quality, optimize=True)
        return Screenshot(data=buf.getvalue(), mime_type="image/jpeg", width=img.width, height=img.height)

    async def screen_size(self) -> ScreenSize:
        if self._screen_w == 0:
            await self.screenshot()  # populates cache
        return ScreenSize(width=self._screen_w, height=self._screen_h)

    # ── Mouse ─────────────────────────────────────────────────────────────

    async def _mouse_event(self, buttons: int, x: float, y: float, vwheel: int = 0) -> None:
        """Send a raw mouse event. Coordinates are 0.0–1.0 relative."""
        await self._post("/api/mouse/event", json_data={
            "buttons": buttons,
            "relativeX": x,
            "relativeY": y,
            "verticalWheelDelta": vwheel,
            "horizontalWheelDelta": 0,
            "isAbsoluteMode": True,
            "sensitivity": 1,
        })

    def _px_to_rel(self, px_x: int, px_y: int) -> tuple[float, float]:
        """Convert pixel coordinates to 0.0–1.0 relative coordinates."""
        if self._screen_w == 0 or self._screen_h == 0:
            # Fallback: assume 1920x1080
            return px_x / 1920, px_y / 1080
        return px_x / self._screen_w, px_y / self._screen_h

    async def mouse_move(self, x: int, y: int) -> None:
        rx, ry = self._px_to_rel(x, y)
        await self._mouse_event(0, rx, ry)

    async def mouse_click(self, x: int, y: int, button: str = "left", clicks: int = 1) -> None:
        btn_map = {"left": 1, "right": 2, "middle": 4}
        btn = btn_map.get(button, 1)
        rx, ry = self._px_to_rel(x, y)

        for _ in range(clicks):
            await self._mouse_event(0, rx, ry)       # move
            await asyncio.sleep(0.03)
            await self._mouse_event(btn, rx, ry)      # press
            await self._mouse_event(0, rx, ry)        # release
            await asyncio.sleep(0.03)

    async def mouse_scroll(self, x: int, y: int, amount: int) -> None:
        rx, ry = self._px_to_rel(x, y)
        await self._mouse_event(0, rx, ry)
        await self._mouse_event(0, rx, ry, vwheel=amount)

    # ── Keyboard ──────────────────────────────────────────────────────────

    async def type_text(self, text: str) -> None:
        """Type text using BliKVM's paste API (supports international layouts)."""
        layout = self.config.kvm_keyboard_layout if hasattr(self.config, "blikvm_keyboard_layout") else "en-us"
        await self._post("/api/hid/paste", json_data={"text": text, "lang": layout})

    def _resolve_key(self, key: str) -> str:
        """Map a human-readable key name to a BliKVM HID code."""
        return _KEY_MAP.get(key.lower(), key)

    async def send_key(self, key: str) -> None:
        hid_key = self._resolve_key(key)
        await self._post("/api/hid/events/send_key", json_data={"key": hid_key, "finish": True})

    async def send_shortcut(self, keys: list[str]) -> None:
        hid_keys = [self._resolve_key(k) for k in keys]
        await self._post("/api/hid/shortcuts", json_data={"shortcuts": hid_keys})
        await asyncio.sleep(0.3)

        # Release modifiers to prevent stuck keys
        for k in hid_keys:
            if k in _MODIFIER_KEYS:
                await self._post("/api/hid/events/send_key", json_data={"key": k, "state": False})
                await asyncio.sleep(0.02)

    # ── Power Control (ATX) ───────────────────────────────────────────────

    async def power_on(self) -> None:
        """Short-press the power button (turn on)."""
        await self._post("/api/atx/click", params={"button": "power"})

    async def power_off(self, force: bool = False) -> None:
        """Press power button. force=True → long-press (force shutdown)."""
        button = "forcepower" if force else "power"
        await self._post("/api/atx/click", params={"button": button})

    async def reboot(self) -> None:
        """Press the hardware reset button."""
        await self._post("/api/atx/click", params={"button": "reboot"})

    async def get_power_state(self) -> dict:
        """Query ATX power LED state."""
        try:
            resp = await self._post("/api/atx/state")
            data = resp.json().get("data", {})
            return {
                "is_on": data.get("is_on", False),
                "led_power": data.get("led_power", False),
                "led_hdd": data.get("led_hdd", False),
            }
        except Exception as e:
            logger.warning("Failed to get power state: %s", e)
            return {"is_on": False, "led_power": False, "led_hdd": False}
