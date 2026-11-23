 姓名：曾悦　学号：f25210228  日期：2026-11-23

## 一、实验目标

接上一个现成的 MCP 服务端（HSK 词表查询），用客户端完成「**发现工具 → 调用工具**」两步，并把 Function Calling、MCP、普通 API 调用三者的分工说清楚。

## 二、配置记录

### 2.1 实验环境

| 项目 | 实际值 |
| --- | --- |
| 操作系统 | Windows 11 |
| Python 解释器 | `C:\Users\XPS15\AppData\Local\Programs\Python\Python313\python.exe`（3.13） |
| MCP SDK | `mcp` 2.x（服务端类名为 `MCPServer`；1.x 的 `FastMCP` 在 2.x 已改名） |
| 服务端 | `hsk_mcp_server.py`（`hsk-tools`，仅读本地 `data/生词表.csv`，全程离线） |
| 客户端 | 自写最小客户端 `demo_client.py`，stdio 方式把服务端当作子进程拉起 |

安装命令：`python -m pip install "mcp[cli]"`

### 2.2 客户端配置原文

Python（stdio）配置，`demo_client.py` 中的实际代码：

```python
params = StdioServerParameters(
    command=sys.executable,          # 用当前解释器，避免 PATH 指向另一个没装 mcp 的 Python
    args=["hsk_mcp_server.py"],
)
```

等价的 JSON 配置（供支持 MCP 的桌面客户端使用）：

```json
{"mcpServers": {"hsk-tools": {"command": "python", "args": ["hsk_mcp_server.py"]}}}
```

> 注意：桌面客户端里的 `command` 必须指向**装了 mcp 的那个解释器**（建议写绝对路径）。只写 `python` 时，实际命中的可能是 PATH 里另一个 Python，服务端会报「未找到 MCP 服务端库」。

### 2.3 启动与运行方式

1. 服务端：`python hsk_mcp_server.py` —— 启动后挂起等待连接，**不退出即正常**；
2. 客户端：另开一个终端 `python demo_client.py` —— 客户端负责拉起服务端并完成握手。

## 三、调用证据

### 3.1 工具列表（发现）

`list_tools()` 返回的工具名：

```text
['hsk_level', 'list_by_level']
```

【截图占位：在此粘贴终端运行截图，建议命名 `evidence_tools.png`，与本文档放同一目录】

### 3.2 工具调用（执行）

调用 `hsk_level("把")` 的返回：

```text
把 -> 3 级
```

补充验证：`list_by_level("1")` 返回 `该等级暂无词汇`——生词表中确实没有 1 级词，这是**正确的工具行为**，不是报错。

【截图占位：在此粘贴调用返回截图，建议命名 `evidence_call.png`】

### 3.3 能力边界观察

服务端只暴露两个工具。向它询问工具能力之外的问题（如天气、翻译整段文章），只会得到「未找到」或「该等级暂无词汇」。这说明**工具能做什么由服务端定义，不是模型「懂不懂」的问题**；模型只负责在 Function Calling 里决定调哪个工具、传什么参数。

## 四、三者辨析

| 维度 | Function Calling | MCP | 普通 API 调用 |
| --- | --- | --- | --- |
| 在哪一侧 | 模型侧 | 工具侧 | 程序侧 |
| 解决什么 | 模型怎么「点名」要调哪个工具 | 工具怎么被统一发现和调用 | 代码怎么直接请求一个服务 |
| 谁定接口 | 模型与应用之间的调用格式 | 工具提供方与使用方之间的协议 | 服务提供方的 API 文档 |
| 本课程对应 | W9 `tool_agent.py` 的 `TOOLS` 字典与 `run()` | W10 `hsk_mcp_server.py` 与客户端配置 | W4 `week4_api_bot.py` 调 DeepSeek |

**三句话（判分口径）：**

1. **Function Calling 是模型侧机制**：模型根据工具描述决定「要不要调、调哪个、传什么参数」。
2. **MCP 是工具侧协议**：把工具怎么暴露、怎么发现、怎么调用定成统一标准，换工具不用换适配层。
3. **普通 API 调用是程序侧直连**：代码直接按服务商文档发请求，中间没有模型决策参与。

三者不冲突，是叠着用的：模型用 Function Calling 做决策，工具用 MCP 标准化接入，底层请求仍是一次普通的 API/进程调用。

**易错点**：MCP = Model Context Protocol（模型上下文协议），**不是**模型压缩或量化（那是第 5 讲的 Quantization），两个缩写撞脸但毫无关系。

## 五、排错记录（本次实际遇到）

1. **`IndentationError: expected an indented block after function definition on line 8`**
   原因：代码粘贴进编辑器时缩进丢失，`async def main():` 下面的语句全部顶格。
   处理：函数体统一 4 空格缩进；`async with` 逐层递进。

2. **服务端启动即退出，报「未找到 MCP 服务端库」**
   原因：客户端里 `command="python"`，命中的是 PATH 中另一个未安装 mcp 的解释器，与运行客户端的 Python 不是同一个。
   处理：改为 `command=sys.executable`，服务端与客户端强制使用同一解释器，问题消失。

3. **`ImportError: mcp.server.fastmcp`**
   原因：装的是 mcp 2.x，`FastMCP` 已改名为 `MCPServer`。
   处理：沿用骨架的两级 `try` 版本自适应写法，1.x / 2.x 都能跑；或 `pip install "mcp<2"` 固定旧版。

## 六、安全说明

- `hsk_mcp_server.py` 只读取本地 `data/生词表.csv`，不发网络请求，是无副作用的安全示范；
- 实验过程中未使用任何真实 API Key，`.env` 未改动、未入仓；
- 结论：MCP 服务端是「别人写的、跑在你机器上的代码」，接入第三方服务前要先看它读什么文件、发什么请求。

## 七、结论

一个 MCP 工具要被客户端正确识别，三件事缺一不可：`@mcp.tool()` 装饰器声明工具、类型注解生成参数表、docstring 提供工具说明。客户端只做两步——`list_tools()` 发现、`call_tool()` 调用；至于工具在哪、怎么启动，由配置里的 `command` / `args` 决定。
