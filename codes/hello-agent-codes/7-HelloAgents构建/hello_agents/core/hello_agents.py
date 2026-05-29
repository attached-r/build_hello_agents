import os
from openai import OpenAI
from dotenv import load_dotenv
from typing import List, Dict, Optional

load_dotenv()

# ---------------------------------------------------------------------------
# Provider 注册表 —— 添加新供应商只需在这里注册
# ---------------------------------------------------------------------------
PROVIDER_CONFIG = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY",
    },
    "modelscope": {
        "base_url": "https://api-inference.modelscope.cn/v1/",
        "api_key_env": "MODELSCOPE_API_KEY",
    },
    "zhipu": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4/",
        "api_key_env": "ZHIPU_API_KEY",
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1/",
        "api_key_env": None,          # Ollama 不需要 API Key
    },
    "vllm": {
        "base_url": "http://localhost:8000/v1/",
        "api_key_env": None,
    },
}
#? 猜测提供商
def _guess_provider_from_url(base_url: str) -> Optional[str]:
    """根据 base_url 猜测提供商"""
    url = base_url.lower()
    if "api-inference.modelscope.cn" in url:
        return "modelscope"
    if "open.bigmodel.cn" in url:
        return "zhipu"
    if "api.openai.com" in url:
        return "openai"
    if "localhost" in url or "127.0.0.1" in url:
        if ":11434" in url:
            return "ollama"
        if ":8000" in url:
            return "vllm"
        return "local"
    return None

#? 猜测提供商
def _guess_provider_from_key(api_key: str) -> Optional[str]:
    """根据 API Key 前缀猜测提供商"""
    if api_key.startswith("ms-"):
        return "modelscope"
    if api_key.startswith("sk-"):
        return "openai"  # 仅是猜测；也可能是兼容 OpenAI 接口的其他服务
    return None


class HelloAgentsLLM:
    """
    多供应商 LLM 客户端。支持任何兼容 OpenAI 接口的服务。
    通过 PROVIDER_CONFIG 注册表管理不同供应商的默认配置。
    """

    def __init__(
        self,
        model: str = None,
        apiKey: str = None,
        baseUrl: str = None,
        provider: str = "auto",       # "auto" / "openai" / "modelscope" / 等
        timeout: int = None,
        **kwargs,
    ):
        # 1) 解析 provider ---------------------------------------------------
        if provider == "auto":
            provider = self._auto_detect_provider(apiKey, baseUrl)
        self.provider = provider

        # 2) 解析最终使用的 apiKey / baseUrl ---------------------------------
        apiKey, baseUrl = self._resolve_credentials(apiKey, baseUrl)

        # 3) 解析模型 ID / 超时 ----------------------------------------------
        self.model = model or os.getenv("LLM_MODEL_ID")
        timeout = timeout or int(os.getenv("LLM_TIMEOUT", "60"))

        if not all([self.model, apiKey, baseUrl]):
            raise ValueError(
                "模型ID、API密钥和服务地址必须被提供或在 .env 文件中定义。"
            )

        # 4) 创建客户端 -------------------------------------------------------
        self.client = OpenAI(api_key=apiKey, base_url=baseUrl, timeout=timeout)

    # ------------------------------------------------------------------
    # Provider 自动检测
    # ------------------------------------------------------------------
    def _auto_detect_provider(self, api_key: Optional[str], base_url: Optional[str]) -> str:
        """按优先级检测：环境变量 > base_url 推断 > API Key 推断"""

        # 1) 按环境变量精确匹配（最高优先级）
        for name, cfg in PROVIDER_CONFIG.items():
            if cfg["api_key_env"] and os.getenv(cfg["api_key_env"]):
                return name

        actual_base_url = base_url or os.getenv("LLM_BASE_URL")
        actual_api_key = api_key or os.getenv("LLM_API_KEY")

        # 2) 根据 base_url 推断
        if actual_base_url:
            guessed = _guess_provider_from_url(actual_base_url)
            if guessed:
                return guessed

        # 3) 根据 API Key 前缀推断
        if actual_api_key:
            guessed = _guess_provider_from_key(actual_api_key)
            if guessed:
                return guessed

        # 4) 兜底 —— 按通用 OpenAI 兼容处理
        return "openai"

    # ------------------------------------------------------------------
    # 凭据解析
    # ------------------------------------------------------------------
    def _resolve_credentials(self, api_key: Optional[str], base_url: Optional[str]) -> tuple:
        """
        根据 self.provider 返回确定的 (api_key, base_url)。
        优先级：调用时传入 > 供应商专用环境变量 > LLM_* 通用变量 > 注册表默认值
        """
        cfg = PROVIDER_CONFIG.get(self.provider)

        if cfg is None:
            # 未知 provider —— 直接用 LLM_* 通用变量或原始值
            resolved_key = api_key or os.getenv("LLM_API_KEY")
            resolved_url = base_url or os.getenv("LLM_BASE_URL")
            return resolved_key, resolved_url

        # 供应商专用环境变量
        env_key = os.getenv(cfg["api_key_env"]) if cfg.get("api_key_env") else None

        resolved_key = api_key or env_key or os.getenv("LLM_API_KEY")
        resolved_url = base_url or os.getenv("LLM_BASE_URL") or cfg["base_url"]

        return resolved_key, resolved_url

    # ------------------------------------------------------------------
    # 核心推理方法
    # ------------------------------------------------------------------
    def think(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0,
        stream: bool = True,
    ) -> Optional[str]:
        """调用大语言模型进行推理。"""
        print(f"🧠 正在调用 [{self.provider}] {self.model} ...")

        # 某些本地 provider (Ollama) 对流式支持不稳定，首次失败可降级
        for attempt, use_stream in [(1, stream), (2, False)]:
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    stream=use_stream,
                )
            except Exception as e:
                print(f"❌ 第 {attempt} 次请求失败: {e}")
                if attempt == 2:   # 非流式也失败了
                    return None
                continue

            if not use_stream:
                return response.choices[0].message.content

            # 流式输出
            print("✅ 响应中:")
            collected: List[str] = []
            for chunk in response:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    print(delta, end="", flush=True)
                collected.append(delta)
            print()
            return "".join(collected)

        return None


# --- 使用示例 ----------------------------------------------------------------
if __name__ == "__main__":
    llm = HelloAgentsLLM()
    msgs = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "写一段 Python 快速排序"},
    ]
    result = llm.think(msgs)
    if result:
        print(f"\n--- 完整响应 ({len(result)} chars) ---\n{result}")


