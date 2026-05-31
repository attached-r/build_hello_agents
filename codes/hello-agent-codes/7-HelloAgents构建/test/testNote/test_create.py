import sys
import os
# 将项目根目录加入模块搜索路径，确保 import hello_agents 能正常找到
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from hello_agents.tools import NoteTool


if __name__ == "__main__":
    notes = NoteTool(workspace="./project_notes")

    note_id = notes.run({
        "action": "create",
        "title": "重构项目 - 第一阶段",
        "content": """## 完成情况
已完成数据模型层的重构,测试覆盖率达到85%。

## 下一步
重构业务逻辑层""",
        "note_type": "task_state",
        "tags": ["refactoring", "phase1"]
    })

    print(f"✅ 笔记创建成功,ID: {note_id}")
