---
name: note-tool-contextbuilder-integration
description: NoteTool 与 ContextBuilder 集成方案总结，含数据流、核心代码和关键设计点
metadata:
  type: reference
---

# NoteTool + ContextBuilder 集成方案

## 一、为什么需要集成？

| 组件 | 职责 | 单独使用的问题 |
|------|------|---------------|
| **NoteTool** | 管理笔记 CRUD（创建/读取/搜索/更新/删除/摘要） | 笔记只是静态文件，LLM 看不到 |
| **ContextBuilder** | GSSC 流水线：Gather → Select → Structure → Compress | 没有"笔记"这个信息源，缺少项目长期上下文 |

**集成价值：** NoteTool 作为 ContextBuilder 的**自定义信息源**，将历史笔记注入 GSSC 流水线，让 LLM 在回答时感知项目进展和历史决策。

---

## 二、数据流

```
用户输入
  │
  ▼
NoteTool 检索笔记
  ├─ list blocker 类型（阻塞问题优先）
  └─ search 全文搜索（匹配用户问题）
  │
  ▼
笔记 → ContextPacket（GSSC 自定义信息包）
  │
  ▼
ContextBuilder.build() ← GSSC 流水线
  ├─ Gather:    汇集 系统指令 + 记忆 + RAG + 对话历史 + 笔记包
  ├─ Select:    评分排序 + 贪心裁剪（预算内取高价值信息）
  ├─ Structure: 组织为 [Role]/[Task]/[Evidence]/[Context]/[Output] 模板
  └─ Compress:  超限兜底压缩
  │
  ▼
结构化上下文 → LLM.think() → 回复
  │
  ▼（可选）
NoteTool.create() ← 自动保存本次交互为笔记
```

---

## 三、核心实现（三段式）

### 第一段：初始化

```python
class ProjectAssistant(SimpleAgent):
    def __init__(self, name: str, project_name: str, llm=None):
        super().__init__(name=name, llm=llm or HelloAgentsLLM())

        # 1. 笔记工具
        self.note_tool = NoteTool(workspace=f"./{project_name}_notes")

        # 2. 记忆系统（给 ContextBuilder 的底层接口，不是给 Agent 调用的 Tool）
        self.memory_manager = MemoryManager(user_id=project_name)

        # 3. RAG 知识库
        self.rag_pipeline = RAGPipeline(llm=self.llm, collection_name=f"{project_name}_kb")

        # 4. 上下文构建器（GSSC 流水线）
        self.context_builder = ContextBuilder(
            memory=self.memory_manager,    # ← 传 MemoryManager，不是 MemoryTool
            rag=self.rag_pipeline,         # ← 传 RAGPipeline，不是 RAGTool
            config=ContextConfig(max_tokens=4000),
        )
```

### 第二段：笔记 → ContextPacket

```python
def _notes_to_packets(self, notes: List[Dict]) -> List[ContextPacket]:
    """将笔记列表转换为 ContextPacket，供 ContextBuilder 消费"""
    packets = []
    for note in notes:
        packets.append(ContextPacket(
            content=f"[笔记:{note['title']}]\n{note['content']}",
            timestamp=datetime.fromisoformat(note['updated_at']),
            token_count=max(1, len(note['content']) // 4),
            relevance_score=0.75,                              # 笔记相关性较高
            metadata={"type": "note", "note_type": note['type']},
        ))
    return packets
```

### 第三段：主流程

```python
def run(self, user_input: str, note_as_action: bool = False) -> str:
    # 1. 检索相关笔记
    notes = self.note_tool.run({"action": "search", "query": user_input, "limit": 3})

    # 2. 笔记 → ContextPacket
    note_packets = self._notes_to_packets(notes)

    # 3. GSSC 流水线构建上下文
    context = self.context_builder.build(
        user_query=user_input,
        conversation_history=self.conversation_history,
        system_instructions=self._build_system_instructions(),
        custom_packets=note_packets,          # ← 笔记从这里注入
    )

    # 4. 调用 LLM
    response = self.llm.think([
        {"role": "system", "content": context},
        {"role": "user", "content": user_input},
    ])

    # 5. 可选：自动保存为笔记
    if note_as_action:
        self.note_tool.run({"action": "create", ...})

    return response
```

---

## 四、设计要点

### 1. ContextBuilder 需要底层接口，不是 Tool 包装

```python
# ❌ 错误：ContextBuilder 拒绝 MemoryTool/RAGTool
self.context_builder = ContextBuilder(memory=MemoryTool(...), rag=RAGTool(...))

# ✅ 正确：传 MemoryManager 和 RAGPipeline
self.context_builder = ContextBuilder(memory=MemoryManager(...), rag=RAGPipeline(...))
```

原因：ContextBuilder 在 GSSC 的 Gather 阶段直接调用 `memory.search()` 和 `rag.query()`，而 Tool 包装的是字符串输入输出，不是结构化接口。

### 2. NoteTool 的 `run()` 返回类型多样

| action | 返回类型 | 使用方式 |
|--------|---------|---------|
| `create` | `str`（note_id） | 直接用于创建 |
| `read` | `Dict` | `note["metadata"]` / `note["content"]` |
| `search` | `List[Dict]` | 遍历，每个元素有 `note_id`/`title`/`content`/`updated_at` |
| `list` | `List[Dict]` | 同上，但只有索引元数据（无 content） |
| `delete` | `str` | 提示消息 |
| `summary` | `Dict` | 统计数据 |

集成时建议加 `isinstance()` 保护：
```python
result = self.note_tool.run({"action": "search", ...})
if isinstance(result, list):
    for note in result:
        ...
```

### 3. 多源去重

当同时使用 `list`（按类型过滤）和 `search`（全文搜索）时，结果可能重叠，建议按 `note_id` 去重：

```python
seen = set()
for note in combined:
    if note.get("note_id") not in seen:
        seen.add(note["note_id"])
        final.append(note)
```

### 4. file_path 保护

`file_path` 只存在索引中，**不在** Markdown 文件的 YAML 元数据里。所以：
- `_read_note` 从索引取 `file_path` ✅
- `_update_note` 写回索引时要恢复 `file_path`（否则下次读取会 `KeyError`）✅ 已在 `_update_note` 中修复

---

## 五、运行效果

两次交互后调用 `note_tool.run({"action": "summary"})` 输出示例：

```json
{
  "total_notes": 1,
  "type_distribution": {"action": 1},
  "recent_notes": [
    {
      "id": "note_20260531_150440_0",
      "title": "我们已经完成了数据模型层的重构...",
      "type": "action",
      "updated_at": "2026-05-31T15:04:40.016606"
    }
  ]
}
```

---

## 六、完整代码

见：`test/testNote/noteTool_with_contextBuilder/ProjectAssistant.py`

```bash
cd 7-HelloAgents构建
python test/testNote/noteTool_with_contextBuilder/ProjectAssistant.py
```
