# 作业 2 验证脚本：确认第 3 个工具 count_by_level 已注册并能调用
# 运行：python demo_client_extra.py（与本文件同目录的 hsk_mcp_server.py 会被自动拉起）
import asyncio
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

HERE = os.path.dirname(os.path.abspath(__file__))


async def main():
    params = StdioServerParameters(
        command=sys.executable,          # 与服务端共用同一解释器，避免 PATH 命中别的 Python
        args=[os.path.join(HERE, "hsk_mcp_server.py")],
    )
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            tools = await s.list_tools()
            print("工具列表：", [t.name for t in tools.tools])
            for level in ("3", "5", "1"):
                res = await s.call_tool("count_by_level", {"level": level})
                print("count_by_level(%s) -> %s" % (level, res.content[0].text))


asyncio.run(main())

