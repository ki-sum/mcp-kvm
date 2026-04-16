"""mcp-kvm CLI — simple commands for inspection and manual use.

Most users won't touch this directly; the primary interface is the MCP
server started via `mcp-kvm-server` (or `uvx mcp-kvm-server`).
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from mcp_kvm import __version__


def _cmd_version(_args: argparse.Namespace) -> int:
    print(f"mcp-kvm {__version__}")
    return 0


def _cmd_test_screenshot(_args: argparse.Namespace) -> int:
    """Quick sanity check — capture one screenshot and save to disk."""
    from mcp_kvm.adapters import create_adapter
    from mcp_kvm.config import Config

    async def run():
        config = Config.from_env()
        adapter = create_adapter(config)
        shot = await adapter.screenshot()
        out = "mcp-kvm-test-screenshot.jpg"
        with open(out, "wb") as f:
            f.write(shot.data)
        print(f"Saved {shot.width}x{shot.height} screenshot -> {out}")
        print(f"Adapter: {adapter.name}")
        await adapter.close()

    asyncio.run(run())
    return 0


def _cmd_server(_args: argparse.Namespace) -> int:
    """Alias for `mcp-kvm-server`."""
    from mcp_kvm.server import main as server_main

    server_main()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="mcp-kvm",
        description="MCP server for AI-controlled KVM automation",
    )
    parser.add_argument("--version", action="store_true", help="Print version and exit")

    sub = parser.add_subparsers(dest="command")

    sp_server = sub.add_parser("server", help="Start the MCP server (stdio)")
    sp_server.set_defaults(func=_cmd_server)

    sp_test = sub.add_parser("test-screenshot", help="Capture one screenshot as a sanity check")
    sp_test.set_defaults(func=_cmd_test_screenshot)

    args = parser.parse_args()

    if args.version:
        return _cmd_version(args)

    if getattr(args, "func", None):
        return args.func(args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
