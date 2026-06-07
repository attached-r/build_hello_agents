#!/usr/bin/env python3
"""最简 MCP 服务端 — 用于测试 stdio 通信"""
import sys
sys.path.insert(0, ".")

from fastmcp import FastMCP

server = FastMCP("MiniServer")

@server.tool()
def ping(msg: str = "pong") -> str:
    return f"echo: {msg}"

if __name__ == "__main__":
    server.run(transport="stdio")
