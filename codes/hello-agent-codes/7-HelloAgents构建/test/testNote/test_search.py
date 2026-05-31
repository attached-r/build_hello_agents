import sys
import os
# 将项目根目录加入模块搜索路径，确保 import hello_agents 能正常找到
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from hello_agents.tools import NoteTool


if __name__ == "__main__":
    notes = NoteTool(workspace="./project_notes")

    result = notes.run({
        "action": "search",
        "query": "重构",
        "limit": 5,
    })
    print(result)
