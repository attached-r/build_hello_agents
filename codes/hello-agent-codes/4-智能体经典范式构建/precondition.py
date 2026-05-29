
#! 前置条件 确保是否按照好了拓展

#? 导入必要的库
import os                        # 用于访问环境变量
from openai import OpenAI        # 从OpenAI API获取响应
from dotenv import load_dotenv   # 从环境变量中加载配置
from typing import List, Dict    # dict 用于定义消息格式

#! 封装llm基础调用函数

# 加载 .env 文件中的环境变量
load_dotenv()

class HelloAgentsLLM:
    """
    为本书 "Hello Agents" 定制的LLM客户端。
    它用于调用任何兼容OpenAI接口的服务，并默认使用流式响应。
    """
    def __init__(self, model: str = None, apiKey: str = None, baseUrl: str = None, timeout: int = None):
        """
        初始化客户端。优先使用传入参数，如果未提供，则从环境变量加载。
        """
        self.model = model or os.getenv("LLM_MODEL_ID")
        apiKey = apiKey or os.getenv("LLM_API_KEY")
        baseUrl = baseUrl or os.getenv("LLM_BASE_URL")
        timeout = timeout or int(os.getenv("LLM_TIMEOUT", 60))   # 默认超时时间60秒
        
        if not all([self.model, apiKey, baseUrl]):
            raise ValueError("模型ID、API密钥和服务地址必须被提供或在.env文件中定义。")
        #? 注册client客户端 提供参数，包括模型ID、API密钥、服务地址、超时时间
        self.client = OpenAI(api_key=apiKey, base_url=baseUrl, timeout=timeout)

    def think(self, messages: List[Dict[str, str]], temperature: float = 0, stream: bool = True) -> str:
        """
        调用大语言模型进行思考，并返回其响应。
        """
        print(f"🧠 正在调用 {self.model} 模型...")
        try:
            # 对于Ollama，有时流式响应会导致连接问题，因此提供非流式选项
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                stream=stream,
            )
            
            if stream:
                # 处理流式响应
                print("✅ 大语言模型响应成功:")
                collected_content = []
                for chunk in response:
                    if not chunk.choices:
                        continue
                    content = chunk.choices[0].delta.content or ""  #? chunk.choices[0].delta.content 用于获取流式响应中的第一个候选内容部分
                    if content:  # 只有当内容不为空时才打印
                        print(content, end="", flush=True)
                    collected_content.append(content)
                print()  # 在流式输出结束后换行
                return "".join(collected_content)
            else:
                # 非流式响应
                print("✅ 大语言模型响应成功:")
                content = response.choices[0].message.content
                print(content)
                return content

        except Exception as e:
            print(f"❌ 调用LLM API时发生错误: {e}")
            # 如果流式请求失败，尝试非流式请求
            if stream:
                print("🔄 尝试非流式请求...")
                try:
                    response = self.client.chat.compclletions.create(
                        model=self.model,
                        messages=messages,
                        temperature=temperature,
                        stream=False,
                    )
                    content = response.choices[0].message.content
                    print("✅ 非流式响应成功:")
                    print(content)
                    return content
                except Exception as e2:
                    print(f"❌ 非流式请求也失败: {e2}")
                    return None
            return None

# --- 客户端使用示例 ---
if __name__ == '__main__':
    try:
        llmClient = HelloAgentsLLM()
        
        exampleMessages = [
            {"role": "system", "content": "You are a helpful assistant that writes Python code."},
            {"role": "user", "content": "写一个快速排序算法"}
        ]
        
        print("--- 调用LLM ---")
        responseText = llmClient.think(exampleMessages)
        if responseText:
            print("\n\n--- 完整模型响应 ---")
            print(responseText)

    except ValueError as e:
        print(e)