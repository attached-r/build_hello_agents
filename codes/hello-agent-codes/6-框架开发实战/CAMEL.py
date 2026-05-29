from colorama import Fore                       # 导入颜色ama库，用于打印彩色文本
from camel.societies import RolePlaying         # 导入角色协作智能体
from camel.utils import print_text_animated     # 导入打印动画函数
from camel.models import ModelFactory           # 导入模型工厂类
from camel.types import ModelPlatformType       # 导入模型平台类型枚举
from dotenv import load_dotenv 
import os

load_dotenv()
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_BASE_URL = os.getenv("LLM_BASE_URL")
LLM_MODEL = os.getenv("LLM_MODEL_ID")

#!创建模型,在这里以ollama为例,调用的ollama模型平台API
model = ModelFactory.create(
    model_platform=ModelPlatformType.OLLAMA,
    model_type=LLM_MODEL,
    url=LLM_BASE_URL,
    api_key=LLM_API_KEY
)

#! 定义协作任务
task_prompt = """
创作一本关于"拖延症心理学"的短篇电子书，目标读者是对心理学感兴趣的普通大众。
要求：
1. 内容科学严谨，基于实证研究
2. 语言通俗易懂，避免过多专业术语
3. 包含实用的改善建议和案例分析
4. 篇幅控制在2000-3000字之间，中文回答
5. 结构清晰，包含引言、核心章节和总结
"""

print(Fore.YELLOW + f"协作任务:\n{task_prompt}\n")    # 打印协作任务，使用黄色字体


#! 初始化角色扮演会话
#? AI 作家作为 "user"，负责提出写作结构和要求
#? AI 心理学家作为 "assistant"，负责提供专业知识和内容
role_play_session = RolePlaying(
    assistant_role_name="心理学家",
    user_role_name="作家",
    task_prompt=task_prompt,
    model=model,
    with_task_specify=False, # 在本例中，我们直接使用给定的task_prompt
)

print(Fore.CYAN + f"具体任务描述:\n{role_play_session.task_prompt}\n")

#! 开始协作对话
import time
chat_turn_limit, n = 30, 0    #? 最大对话轮次，防止无限循环
# 调用 init_chat() 来获得由 AI 生成的初始对话消息
try:
    input_msg = role_play_session.init_chat()
except Exception as e:
    print(f"{Fore.RED}初始化聊天时出错: {e}\n")
    exit(1)

while n < chat_turn_limit:
    n += 1
    try:
        #? step() 方法驱动一轮完整的对话，AI 用户和 AI 助理各发言一次
        assistant_response, user_response = role_play_session.step(input_msg)
    except Exception as e:
        print(f"{Fore.RED}第 {n} 轮对话时出错: {e}\n")
        print(f"{Fore.YELLOW}等待几秒后重试...")
        time.sleep(5)
        continue  # 继续下一轮循环
    
    # 检查是否有消息返回，防止对话提前终止
    if assistant_response.msg is None or user_response.msg is None:
        print(f"{Fore.RED}收到空消息，结束对话")
        break
    
    print_text_animated(Fore.BLUE + f"作家 (AI User):\n\n{user_response.msg.content}\n")         # 流式打印作家的回复，使用蓝色字体
    print_text_animated(Fore.GREEN + f"心理学家 (AI Assistant):\n\n{assistant_response.msg.content}\n") # 流式打印心理学家的回复，使用绿色字体
    
    # 检查任务完成标志
    if "<CAMEL_TASK_DONE>" in user_response.msg.content or "<CAMEL_TASK_DONE>" in assistant_response.msg.content:
        print(Fore.MAGENTA + "✅ 电子书创作完成！")
        break
    
    # 将助理的回复作为下一轮对话的输入
    input_msg = assistant_response.msg

print(Fore.BLUE + f"总共进行了 {n} 轮协作对话")