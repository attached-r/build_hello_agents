"""
和 MemoryTool 集成的测试: 探索项目结构 → 存入 Neo4j 图库。

流程:
  1. 用 TerminalTool 验证目录可达
  2. 用 os.walk 遍历目录结构，构建实体 + 关系
  3. 写入 Neo4j 图库
"""

import sys
import os
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from hello_agents.tools.builtin.terminal_tool import TerminalTool


def walk_to_entities(root_dir: str) -> tuple[list[dict], list[dict]]:
    """用 os.walk 遍历目录，返回实体 + 关系列表。"""
    entities: list[dict] = []
    relations: list[dict] = []
    seen: dict[str, str] = {}  # 相对路径 → entity_id

    def _ensure(parent_path: str, name: str, is_dir: bool) -> str:
        """确保实体存在，返回 entity_id。"""
        full = os.path.join(parent_path, name).replace("\\", "/")
        if full in seen:
            return seen[full]
        eid = uuid.uuid4().hex[:12]
        entities.append({
            "entity_id": eid,
            "name": name,
            "type": "directory" if is_dir else "file",
        })
        seen[full] = eid
        if parent_path and parent_path in seen:
            relations.append({
                "subject_id": seen[parent_path],
                "object_id": eid,
                "type": "contains",
            })
        return eid

    root_name = os.path.basename(os.path.normpath(root_dir))
    _ensure("", root_name, is_dir=True)

    for current_dir, dirs, files in os.walk(root_dir):
        rel = os.path.relpath(current_dir, os.path.dirname(root_dir)).replace("\\", "/")
        for d in sorted(dirs):
            _ensure(rel, d, is_dir=True)
        for f in sorted(files):
            _ensure(rel, f, is_dir=False)

    return entities, relations


# ── 主逻辑 ───────────────────────────────────────────────

WORKSPACE = os.path.dirname(os.path.abspath(__file__))
while not os.path.isdir(os.path.join(WORKSPACE, "hello_agents")):
    WORKSPACE = os.path.dirname(WORKSPACE)
    if os.path.dirname(WORKSPACE) == WORKSPACE:
        WORKSPACE = os.path.dirname(os.path.abspath(__file__))
        break

terminal = TerminalTool(workspace=WORKSPACE, timeout=15, allow_cd=True)
print(f"📂 工作空间: {WORKSPACE}\n")

# 1. 用 tree 确认目录可达（/F 不加，只验证存在）
check = terminal.run({"command": "tree hello_agents", "description": "验证目录"})
if "安全校验失败" in check:
    print("⚠️  tree 不可用，跳过验证（os.walk 兜底）")
else:
    print(f"📋 {check.splitlines()[0]}\n")

# 2. os.walk 遍历目录结构（只解析 tools 子目录，减少节点量）
hello_dir = os.path.join(WORKSPACE, "hello_agents")
entities, relations = walk_to_entities(os.path.join(hello_dir, "tools"))
print(f"解析到 {len(entities)} 个实体, {len(relations)} 条关系")

# 3. 写入 Neo4j
try:
    from hello_agents.memory.storage.neo4j_store import Neo4jGraphStore
    store = Neo4jGraphStore()

    deleted = store.clear_all()
    print(f"已清空 {deleted} 个旧节点")

    for e in entities:
        store.create_entity(
            entity_id=e["entity_id"],
            name=e["name"],
            entity_type=e["type"],
        )
    print(f"✅ 已创建 {len(entities)} 个实体节点")

    for r in relations:
        store.create_relation(
            subject_id=r["subject_id"],
            object_id=r["object_id"],
            relation_type=r["type"],
        )
    print(f"✅ 已创建 {len(relations)} 条关系")

    print(f"\n📊 Neo4j 统计: {store.count_entities()} 实体, {store.count_relations()} 关系")
    store.close()

except Exception as e:
    print(f"❌ Neo4j 写入失败: {e}")
