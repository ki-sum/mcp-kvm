"""KVMAdapter — abstract base class for all adapter implementations.

An adapter is a pluggable backend that knows how to:
  - capture a screenshot from a target machine
  - move / click the mouse
  - type text and send key combinations

Adapters can be hardware (BliKVM, PiKVM) or software (pyautogui on the same
machine that runs the MCP server).

Third parties can implement their own adapter by subclassing KVMAdapter and
registering it via an entry point (see docs/adapters/custom.md).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ScreenSize:
    """Resolution of the target screen."""

    width: int
    height: int


@dataclass
class Screenshot:
    """A captured screenshot — raw bytes plus format metadata."""

    data: bytes  # image bytes
    mime_type: str  # e.g. "image/jpeg" or "image/png"
    width: int
    height: int


class KVMAdapter(ABC):
    """Abstract base class for KVM adapters.

    All methods are async. Implementations should raise exceptions on failure;
    the server layer converts exceptions to structured MCP tool errors.
    """

    name: str  # Human-readable adapter name, e.g. "software", "blikvm"

    @abstractmethod
    async def screen_size(self) -> ScreenSize:
        """Return the current resolution of the target screen."""

    @abstractmethod
    async def screenshot(self) -> Screenshot:
        """Capture the current screen content."""

    @abstractmethod
    async def mouse_move(self, x: int, y: int) -> None:
        """Move mouse to absolute pixel coordinates (x, y)."""

    @abstractmethod
    async def mouse_click(self, x: int, y: int, button: str = "left", clicks: int = 1) -> None:
        """Click at (x, y) with the given button ('left', 'right', 'middle').

        clicks=2 for double-click.
        """

    @abstractmethod
    async def mouse_scroll(self, x: int, y: int, amount: int) -> None:
        """Scroll at (x, y). Positive = up, negative = down."""

    @abstractmethod
    async def type_text(self, text: str) -> None:
        """Type a string of text."""

    @abstractmethod
    async def send_key(self, key: str) -> None:
        """Send a single key press (e.g. 'enter', 'tab', 'escape', 'f1')."""

    @abstractmethod
    async def send_shortcut(self, keys: list[str]) -> None:
        """Send a keyboard shortcut (e.g. ['ctrl', 'c'] for copy)."""

    # ── Power Control (KVM hardware only) ──────────────────────────────

    async def power_on(self) -> None:
        """Short-press the physical power button to turn on the target machine.

        Raises NotImplementedError for software adapters (no ATX control).
        """
        raise NotImplementedError(f"{self.name} adapter does not support ATX power control")

    async def power_off(self, force: bool = False) -> None:
        """Press power button. force=True for long-press (hard shutdown)."""
        raise NotImplementedError(f"{self.name} adapter does not support ATX power control")

    async def reboot(self) -> None:
        """Press the hardware reset button."""
        raise NotImplementedError(f"{self.name} adapter does not support ATX power control")

    async def get_power_state(self) -> dict:
        """Query ATX power LED state. Returns {'is_on': bool, ...}."""
        raise NotImplementedError(f"{self.name} adapter does not support ATX power control")

    @property
    def has_power_control(self) -> bool:
        """Whether this adapter supports ATX power on/off/reboot."""
        return False

    async def close(self) -> None:
        """Release any resources held by the adapter. Default: no-op."""
        return None
