"""
自定义 LLM 客户端 —— 只需两件事：
    1) 指定 provider 名称（与 PROVIDER_CONFIG 中的 key 一致）
    2) 指定模型 ID

其余（base_url、api_key 环境变量名等）由父类的 Provider 注册表自动处理。
"""
from typing import Optional
from hello_agents import HelloAgentsLLM


class MyLLM(HelloAgentsLLM):
    """对 HelloAgentsLLM 的轻量封装，简化调用参数。"""

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        provider: str = "auto",                # 想要用哪个 provider 就写哪个
        **kwargs,
    ):
        # 全部交给父类处理 —— PROVIDER_CONFIG 会搞定默认 base_url 和 env var
        super().__init__(
            model=model,
            apiKey=api_key,
            baseUrl=base_url,
            provider=provider,
            **kwargs,
        )


if __name__ == "__main__":
    # === 快速测试 ===
    test_cases = [
        {"provider": "auto",       "label": "自动检测"},
        {"provider": "openai",     "label": "OpenAI"},
        {"provider": "modelscope", "label": "ModelScope"},
        {"provider": "ollama",     "label": "Ollama（本地）"},
    ]

    for case in test_cases:
        print(f"\n--- 测试: {case['label']} ---")
        try:
            llm = MyLLM(provider=case["provider"])
            result = llm.think([{"role": "user", "content": "说你好"}])
            print(f"结果: {result}")
        except ValueError as e:
            print(f"配置不完整: {e}（可忽略，仅当环境变量就绪时会真正调用）")
