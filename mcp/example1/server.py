"""Example MCP server — replace with your own tools.

Usage:
  1. Rename this directory (e.g., mcp/calculator/)
  2. Update mcp.toml with your entrypoint and dependencies
  3. Add your tools using @mcp.tool()
  4. Set mcp_dir: "mcp" in arena.yaml

See README.md for full documentation.
"""

from fastmcp import FastMCP

mcp = FastMCP("example")


@mcp.tool()
def hello(name: str) -> str:
    """Say hello — replace this with your own tool."""
    return f"Hello, {name}!"
