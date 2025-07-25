# server.py
from fastmcp import FastMCP

mcp = FastMCP("Demo for AI Summer Days MCP workshop")

@mcp.tool
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return int(a) + int(b)

if __name__ == "__main__":
    mcp.run()
