"""Smoke test: start a Synapse-generated MCP server over stdio and call some tools.
Usage: python tools/smoke_mcp.py <server.py> <ENDPOINT_BASE_URL> <tool> [json-args] ..."""
import asyncio
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    server, base = sys.argv[1], sys.argv[2]
    calls = sys.argv[3:]
    params = StdioServerParameters(command=sys.executable, args=[server], env={**os.environ, "ENDPOINT_BASE_URL": base})
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            tools = (await s.list_tools()).tools
            print("tools:", [t.name for t in tools])
            for i in range(0, len(calls), 2):
                name, args = calls[i], json.loads(calls[i + 1]) if i + 1 < len(calls) else {}
                res = await s.call_tool(name, args)
                text = res.content[0].text if res.content else str(res.structuredContent)
                print(f"{name}{args} isError={res.isError} -> {text[:300]}")


asyncio.run(main())
