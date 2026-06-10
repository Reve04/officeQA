"""Utility functions for parsing tables — imported by treasury_mcp.py.

Shows how multi-file MCP servers work: put shared logic in utility
modules and import them from the main server file.
"""

import json


def parse_markdown_table(raw_text: str) -> str:
    """Parse a pipe-delimited markdown table into JSON.

    Replace this with your own parsing logic.
    """