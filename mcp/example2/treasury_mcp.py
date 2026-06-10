"""Treasury MCP server — multi-file example with utility imports.

Shows how to:
  - Use a custom symbol name (treasury_app, not mcp)
  - Import helper functions from a utility module
  - Declare dependencies (pandas) in mcp.toml

Replace with your own domain-specific tools.
"""

from fastmcp import FastMCP

from table_utils import parse_markdown_table

treasury_app = FastMCP("treasury")


@treasury_app.tool()
def parse_table(raw_text: str) -> str:
    """Parse a markdown table into structured JSON.

    Args:
        raw_text: Raw markdown table text with | delimiters.
    """
    return parse_markdown_table(raw_text)
