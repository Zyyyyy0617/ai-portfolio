# W9 手写最小工具调用循环（不用框架）
# 依赖：pip install openai python-dotenv
import os
import csv
import sys
import ast
import json
import re
import operator
import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import weekpath  # noqa: E402  数据路径 + 加载 .env

weekpath.load_env()

import openai  # noqa: E402

VOCAB = weekpath.data_path("生词表.csv")

_client = None


def get_client():
    global _client
    if _client is None:
        key = os.getenv("DEEPSEEK_API_KEY")
        if not key:
            raise RuntimeError("未配置 DEEPSEEK_API_KEY，请先在 .env 中填写")
        _client = openai.OpenAI(base_url="https://api.deepseek.com/v1", api_key=key)
    return _client


def get_time():
    return str(datetime.datetime.now())


# ---- 安全计算：白名单 AST，绝不使用裸 eval ----
_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.USub: operator.neg, ast.UAdd: operator.pos,
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


def calc(expr):
    """教学演示用：只做四则运算。为什么不用 eval？
    因为 eval 会执行任意 Python 代码，是典型的安全反模式（本课程伦理红线之一）。"""
    try:
        return str(_eval_node(ast.parse(str(expr), mode="eval")))
    except ZeroDivisionError:
        return "错误：除数为 0"
    except Exception as e:
        return "拒绝计算：%s" % e


def hsk_level(word):
    with open(VOCAB, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["词汇"].strip() == str(word).strip():
                return "%s 是 %s 级" % (word, row["HSK等级"])
    return "未找到 %s" % word


TOOLS = {"get_time": get_time, "calc": calc, "hsk_level": hsk_level}

SYS = ("你是国际中文助教。可用工具只有这3个：get_time（查当前时间，无参数）、"
       "calc（四则运算，如 calc('35*24')）、hsk_level（查生词 HSK 等级，如 hsk_level('把'))。"
       "如需调用，只输出一行 JSON，格式：{'tool': \"工具名\", \"args\": [参数]}；"
       "一次只调用一个工具，绝不编造不存在的工具名；无需工具时直接回答。")


def parse_calls(txt):
    """容错解析：剥掉围栏与客套话，并把单引号转为双引号"""
    s = (txt or "").strip()
    s = s.replace("```json", "").replace("```", "").strip()
    # 尝试直接解析（把单引号换成双引号，解决你截图里的问题）
    try:
        s_fixed = s.replace("'", '"')
        obj = json.loads(s_fixed)
        return [obj] if isinstance(obj, dict) else []
    except Exception:
        pass
        
    # 多个工具调用并列输出时逐块解析
    calls = []
    for blk in re.findall(r"\{[^}]*}", s):
        try:
            blk = blk.replace("'", '"') # 这里也加单引号替换
            obj = json.loads(blk)
            if isinstance(obj, dict):
                calls.append(obj)
        except Exception:
            continue
    return calls


def run(user_msg, max_calls=2):
    print(f"\n【轨迹记录 - 原始问句】: {user_msg}")
    msgs = [{"role": "system", "content": SYS}, {"role": "user", "content": user_msg}]
    
    for _ in range(max_calls):
        txt = get_client().chat.completions.create(
            model="deepseek-chat", messages=msgs).choices[0].message.content
        
        # 这里调用上面改好的 parse_calls
        calls = [c for c in parse_calls(txt)
                 if isinstance(c.get("tool"), str) and c.get("tool") in TOOLS]
                 
        if not calls:
            print(f"【轨迹记录 - 最终回答】: {txt}\n")
            return txt
            
        print(f"【轨迹记录 - 模型输出的JSON】:\n{txt}")
        
        results = []
        # 遍历模型决定调用的所有工具
        for call in calls:
            args = call.get("args") or []
            if not isinstance(args, list):
                results.append("工具参数格式错误：%r" % (args,))
                continue
            try:
                res = TOOLS[call["tool"]](*args)
                print(f"【轨迹记录 - 工具 {call['tool']} 返回值】: {res}")
                results.append("%s%r → %s" % (call["tool"], args, res))
            except Exception as e:
                print(f"【轨迹记录 - 工具执行失败】: {e}")
                results.append("工具执行失败：%s" % e)
                
        # 把结果合并回喂
        msgs += [{"role": "assistant", "content": txt},
                 {"role": "user", "content": "工具返回：%s。请据此作答。" % "; ".join(results)}]

    final_txt = get_client().chat.completions.create(
        model="deepseek-chat", messages=msgs).choices[0].message.content
    print(f"【轨迹记录 - 最终回答】: {final_txt}\n")
    return final_txt


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "'把'字是 HSK 几级词汇？现在几点了？"
    print("用户输入：", q)
    print("助手：", run(q))
