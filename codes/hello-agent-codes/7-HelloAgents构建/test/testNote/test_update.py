import sys
import os
# 将项目根目录加入模块搜索路径，确保 import hello_agents 能正常找到
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from hello_agents.tools import NoteTool

if __name__ == "__main__":
    notes = NoteTool(workspace="./project_notes")
    note_id = "note_20260531_135613_0" 

    # 更新笔记
    result = notes.run({
    "action": "update",
    "note_id": note_id,
    "title": "更新后的标题",
    "content": "更新后的内容",
    "note_type": None,
    "tags": ["important", "done"],
    })

    print(result)