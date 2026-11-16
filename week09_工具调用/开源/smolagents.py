# -*- coding: utf-8 -*-
"""W9 手写循环 → A 层 smolagents 版（ToolCallingAgent）。

运行：
  pip install 'smolagents[openai]' python-dotenv
  python a_layer_smolagents.py --selftest                       # 不联网，只测 4 个工具
  python a_layer_smolagents.py "‘把’字是 HSK 几级词汇？现在几点？"

说明：
  - 保留你 W9 的 3 个工具，并新增第 4 个工具 hsk_words_by_level。
  - 保留 AST 白名单计算，绝不调用裸 eval。
  - 优先使用上级目录的 weekpath.data_path("生词表.csv")；
    若没有 weekpath，则读取本目录的 生词表.csv 或 示例生词表.csv。
"""

import ast
import csv
import datetime
import operator
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

# 升级路线：装上 smolagents 后 @tool 会把函数变成 Tool；
# 未安装时退化为普通函数，只服务 --selftest，不能算 A 层运行证据。
try:
    from smolagents import tool
except ImportError:  # pragma: no cover - 仅离线自检使用
    def tool(fn):
        return fn

try:
    import weekpath  # noqa: E402

    if hasattr(weekpath, "load_env"):
        weekpath.load_env()
except Exception:  # weekpath 不存在或加载失败时走本地 CSV
    weekpath = None


def _resolve_vocab_path() -> Path:
    if weekpath is not None and hasattr(weekpath, "data_path"):
        try:
            return Path(weekpath.data_path("生词表.csv"))
        except Exception:
            pass
    for name in ("生词表.csv", "示例生词表.csv"):
        candidate = HERE / name
        if candidate.exists():
            return candidate
    raise FileNotFoundError("找不到生词表：请放 生词表.csv 到本目录，或配置 weekpath.data_path")


VOCAB = _resolve_vocab_path()

# ---- 安全计算：白名单 AST，绝不使用裸 eval ----
_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _eval_node(node):
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_node(node.operand))
    raise ValueError("只允许数字与 + - * / ** % 运算")


@tool
def get_time() -> str:
    """查询当前系统时间，无参数，返回时间字符串。"""
    return str(datetime.datetime.now())


@tool
def calc(expr: str) -> str:
    """教学演示用安全四则运算：只支持数字与 + - * / ** %，绝不使用 eval。

    Args:
        expr: 要计算的表达式字符串，例如 "35*24"
    """
    try:
        return str(_eval_node(ast.parse(str(expr), mode="eval")))
    except ZeroDivisionError:
        return "错误：除数为 0"
    except Exception as exc:
        return "拒绝计算：%s" % exc


@tool
def hsk_level(word: str) -> str:
    """在生词表中查询词语的 HSK 等级。

    Args:
        word: 要查询的汉字或词语，例如 "把"
    """
    with VOCAB.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            row = {(k or "").strip().lstrip("\ufeff"): v for k, v in row.items()}
            if (row.get("词汇") or "").strip() == str(word).strip():
                return "%s 是 %s 级" % (word, row.get("HSK等级", "未知"))
    return "未找到 %s" % word


@tool
def hsk_words_by_level(level: str) -> str:
    """按 HSK 等级反查生词，最多列出 10 个。

    Args:
        level: HSK 等级，例如 "1" 或 "HSK1"
    """
    target = str(level).strip().lower().replace("hsk", "")
    words = []
    with VOCAB.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            row = {(k or "").strip().lstrip("\ufeff"): v for k, v in row.items()}
            lv = str(row.get("HSK等级", "")).strip().lower().replace("hsk", "")
            if lv == target:
                words.append(str(row.get("词汇", "")).strip())
                if len(words) >= 10:
                    break
    if not words:
        return "未找到 HSK %s 的生词" % level
    return "HSK %s 示例词：%s（共显示 %d 个）" % (level, "、".join(words), len(words))


TOOL_FUNCS = [get_time, calc, hsk_level, hsk_words_by_level]

SYSTEM_PROMPT = (
    "你是国际中文助教。回答要简短，优先使用已提供的工具核实信息，"
    "不要编造工具名或生词表数据；无需工具时直接回答。"
)


def show_tool_schema() -> None:
    """证据 1：@tool 后每个工具的名称、inputs、描述。"""
    print("【工具清单 / Tool.inputs】")
    for item in TOOL_FUNCS:
        name = getattr(item, "name", getattr(item, "__name__", "?"))
        description = getattr(item, "description", item.__doc__ or "").strip().splitlines()[0]
        print("- %s | inputs=%s | %s" % (name, getattr(item, "inputs", None), description))


def build_agent(max_steps: int = 2):
    from smolagents import OpenAIModel, ToolCallingAgent

    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("未配置 DEEPSEEK_API_KEY，请先在 .env 中填写（.env 不要入库）")

    model = OpenAIModel(
        model_id="deepseek-chat",
        api_base="https://api.deepseek.com/v1",
        api_key=api_key,
    )
    try:
        return ToolCallingAgent(
            tools=TOOL_FUNCS,
            model=model,
            max_steps=max_steps,
            instructions=SYSTEM_PROMPT,
        )
    except TypeError:
        # 旧版 smolagents 没有 instructions 参数：工具 docstring 已足够描述用法
        return ToolCallingAgent(tools=TOOL_FUNCS, model=model, max_steps=max_steps)


def run_selftest() -> None:
    print("生词表：", VOCAB)
    print("get_time() ->", get_time())
    print("calc('35*24') ->", calc("35*24"))
    print("calc('__import__(\"os\").system(\"echo pwned\")') ->",
          calc('__import__("os").system("echo pwned")'))
    print("hsk_level('把') ->", hsk_level("把"))
    print("hsk_words_by_level('1') ->", hsk_words_by_level("1"))
    show_tool_schema()


def main() -> None:
    if len(sys.argv) == 2 and sys.argv[1] == "--selftest":
        run_selftest()
        return

    question = " ".join(sys.argv[1:]) or "‘把’字是 HSK 几级词汇？现在几点？"
    show_tool_schema()
    agent = build_agent(max_steps=2)  # 对应 W9 的 max_calls=2
    answer = agent.run(question)

    print("\n【最终回答】\n%s" % answer)
    print("\n【轨迹证据：agent.logs / memory.steps】")
    trace = getattr(agent, "logs", None) or getattr(getattr(agent, "memory", None), "steps", [])
    for index, step in enumerate(trace, 1):
        print("\n--- step %d ---" % index)
        print(step)


if __name__ == "__main__":
    main()
