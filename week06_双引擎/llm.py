# W6 双引擎封装 —— 此后所有周统一经此调用
# 依赖：pip install openai requests python-dotenv
import os
import sys
import time  ###增加时间mod

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import weekpath  # noqa: E402  跨周导入 + 加载 .env

weekpath.load_env()

import requests  # noqa: E402
import openai  # noqa: E402


class LocalEngine:
    """本地引擎（Ollama）：隐私任务优先、断网可用。"""

    def __init__(self, model=None):
        self.model = model or os.getenv("LOCAL_MODEL", "qwen2.5:0.5b")

    def ask(self, prompt, temperature=0.7, max_tokens=800):
        r = requests.post(
            "http://localhost:11434/api/chat",
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "options": {"temperature": temperature, "num_predict": max_tokens},
                "stream": False,
            },
            timeout=60,
        )
        r.raise_for_status()
        return r.json()["message"]["content"]


class APIEngine:
    """云端引擎：复杂任务、本地失败兜底。

    注意：openai.OpenAI(...) 在 api_key 为 None 时会直接抛错。
    若在这里（构造 LLM 时）就建客户端，那么没配密钥的同学连"纯本地"模式都跑不起来。
    因此改为**按需创建**：第一次真正调用云端时才建客户端。
    """

    def __init__(self, base_url=None, model=None):
        self.base_url = base_url or "https://api.deepseek.com/v1"
        self.model = model or "deepseek-chat"
        self._client = None

    def _get_client(self):
        if self._client is None:
            key = os.getenv("DEEPSEEK_API_KEY")
            if not key:
                raise RuntimeError(
                    "未配置 DEEPSEEK_API_KEY：请复制 .env.example 为 .env 并填入密钥，"
                    "或在系统环境变量中设置。纯本地模式请调用 ask(..., prefer='local')。"
                )
            self._client = openai.OpenAI(base_url=self.base_url, api_key=key)
        return self._client

    def ask(self, prompt, temperature=0.7, max_tokens=800):
        r = self._get_client().chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return r.choices[0].message.content


class LLM:
    """统一入口：ask(prompt)。本地优先、云端兜底，增加最多2次重试，重试失败再切换备选引擎。"""
    def __init__(self, local_model=None):
        self.local = LocalEngine(local_model)
        self.api = APIEngine()

    def ask(self, prompt, prefer="local", max_retry=2, **kw):
        if prefer == "local":
            first, second, tag = self.local, self.api, "本地重试耗尽，自动切换云端"
        else:
            first, second, tag = self.api, self.local, "云端重试耗尽，自动切换本地"

        # 优先引擎最多尝试 max_retry+1 次（原始1次 + max_retry次重试）
        for attempt in range(max_retry + 1):
            try:
                return first.ask(prompt, **kw)
            except Exception as e:
                print(f"[{tag}] 第{attempt+1}次调用失败: {e}")
                time.sleep(0.8)
        
        print(f"[{tag}] {max_retry}次重试全部失败，切换备选引擎")
        return second.ask(prompt,**kw)    ######选择失败重试，最多 2 次重试，适用于网络抖动、API 瞬时限流这类临时故障；区别于引擎切换，重试优先尝试当前优选引擎，重试耗尽才切换备选引擎，减少不必要的引擎切换开销。



if __name__ == "__main__":
    llm = LLM()
    print(llm.ask("给《愚公移山》出一道 HSK4 阅读理解题", prefer="local"))
