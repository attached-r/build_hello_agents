# 笔记工具

from typing import Optional, List, Dict, Tuple, Any
from datetime import datetime
import json                         # 用于 JSON 格式索引
import os                           # 用于路径操作
import yaml                         # 用于处理 YAML 格式


class NoteTool:
    def __init__(self, workspace: str, index: Optional[Dict] = None):
        self.workspace = workspace
        self.index = index if index is not None else {}
        self._load_index()

        """
        初始化笔记工具，加载索引
        Args:
            workspace: 工作空间目录，用于存储笔记文件
            index: 可选的索引字典，用于初始化索引
        """

    # ── 索引持久化 ──────────────────────────────────────────────────────

    def _load_index(self):
        """从 workspace/notes_index.json 加载索引，不存在则初始化为空字典"""
        index_path = os.path.join(self.workspace, "notes_index.json")
        if os.path.exists(index_path):
            with open(index_path, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
                self.index = loaded if isinstance(loaded, dict) else {}
        else:
            self.index = {}

    def _save_index(self):
        """将索引保存到 workspace/notes_index.json"""
        os.makedirs(self.workspace, exist_ok=True)
        index_path = os.path.join(self.workspace, "notes_index.json")
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(self.index, f, ensure_ascii=False, indent=2)

    # ── 统一入口 ────────────────────────────────────────────────────────

    def run(self, params: Dict) -> Any:
        """统一入口，根据 action 分发到具体操作

        Args:
            params: 参数字典，必须含 "action" 键

        Returns:
            str: 操作结果（如笔记ID）
        """
        action = params.get("action")
        if action == "create":
            return self._create_note(
                title=params["title"],
                content=params["content"],
                note_type=params.get("note_type", "general"),
                tags=params.get("tags"),
            )
        elif action == "read":
            return self._read_note(params["note_id"])
        elif action == "update":
            return self._update_note(
                note_id=params["note_id"],
                title=params.get("title"),
                content=params.get("content"),
                note_type=params.get("note_type"),
                tags=params.get("tags"),
            )
        elif action == "search":
            return self._search_notes(
                query=params["query"],
                limit=params.get("limit", 10),
                note_type=params.get("note_type"),
                tags=params.get("tags"),
            )
        elif action == "list":
            return self._list_notes(
                note_type=params.get("note_type"),
                tags=params.get("tags"),
                limit=params.get("limit", 20),
            )
        elif action == "summary":
            return self._summary()
        elif action == "delete":
            return self._delete_note(params["note_id"])
        else:
            raise ValueError(f"未知 action: {action}")

    #? ── 1. 创建笔记 ────────────────────────────────────────────────────────

    def _create_note(
        self,
        title: str,
        content: str,
        note_type: str = "general",
        tags: Optional[List[str]] = None,
    ) -> str:
        """创建笔记

        Args:
            title: 笔记标题
            content: 笔记内容(Markdown格式)
            note_type: 笔记类型(task_state/conclusion/blocker/action/reference/general)
            tags: 标签列表

        Returns:
            str: 笔记ID
        """
        # 1. 确保 workspace 目录存在
        os.makedirs(self.workspace, exist_ok=True)

        # 2. 生成唯一ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        note_id = f"note_{timestamp}_{len(self.index)}"

        # 3. 构建元数据
        metadata = {
            "id": note_id,
            "title": title,
            "type": note_type,
            "tags": tags or [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        # 4. 构建完整的 Markdown 文件内容
        md_content = self._build_markdown(metadata, content)

        # 5. 保存到文件 路径: workspace/note_id.md
        file_path = os.path.join(self.workspace, f"{note_id}.md")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        # 6. 更新索引
        metadata["file_path"] = file_path
        self.index[note_id] = metadata
        self._save_index()

        return note_id

    # ── Markdown 构建 ──────────────────────────────────────────────────

    def _build_markdown(self, metadata: Dict, content: str) -> str:
        """构建 Markdown 文件内容(YAML 前置元数据 + 正文)"""
        # 1. 构建 YAML 前置元数据
        yaml_header = yaml.dump(metadata, allow_unicode=True, sort_keys=False)
        
        # 2. 构建 Markdown 正文
        return f"---\n{yaml_header}---\n\n{content}"
    

    #? —— 2. 读取笔记内容 ————————————————————————————————————————————————————
    def _read_note(self, note_id: str) -> Dict:
        """读取笔记内容
        Args:
            note_id: 笔记ID

        Returns:
            Dict: 包含元数据和内容的字典
        """
        # 1. 通过索引获取文件路径
        if note_id not in self.index:
            raise ValueError(f"笔记不存在: {note_id}")

        file_path = self.index[note_id]["file_path"]

        # 2. 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_content = f.read()

        # 3. 解析 YAML 元数据和 Markdown 正文
        metadata, content = self._parse_markdown(raw_content)

        return {
            "metadata": metadata,
            "content": content
        }



    # ── Markdown 解析 ──────────────────────────────────────────────────
    def _parse_markdown(self, raw_content: str) -> Tuple[Dict, str]:
        """解析 Markdown 文件(分离 YAML 和正文)"""

        # 查找 YAML 分隔符
        parts = raw_content.split('---\n', 2)   # 最多分割两次,确保有3个部分

        if len(parts) >= 3:
            # 有 YAML 前置元数据
            yaml_str = parts[1]
            content = parts[2].strip()
            metadata = yaml.safe_load(yaml_str)
        else:
            # 无元数据,全部作为正文
            metadata = {}
            content = raw_content.strip()

        return metadata, content


    #? —— 3. 更新笔记 ————————————————————————————————————————————————————
    def _update_note(
        self,
        note_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        note_type: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> str:
        """更新笔记
    
        Args:
            note_id: 笔记ID
            title: 新标题(可选)
            content: 新内容(可选)
            note_type: 新类型(可选)
            tags: 新标签(可选)
    
        Returns:
            str: 操作结果消息
        """
        if note_id not in self.index:
            raise ValueError(f"笔记不存在: {note_id}")
    
        # 1. 读取现有笔记
        note = self._read_note(note_id)
        metadata = note.get("metadata")
        old_content = note.get("content")
    
        # 2. 更新字段
        if title:
            metadata["title"] = title
        if note_type:
            metadata["type"] = note_type
        if tags is not None:
            metadata["tags"] = tags
        if content is not None:
            old_content = content
    
        # 更新时间戳
        metadata["updated_at"] = datetime.now().isoformat()

        # 3. 重新构建并保存（file_path 存于索引中，而非 YAML 元数据）
        md_content = self._build_markdown(metadata, old_content)
        file_path = self.index[note_id]["file_path"]
    
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
    
        # 4. 更新索引（metadata 来自 YAML 解析不含 file_path，从旧索引恢复）
        metadata["file_path"] = self.index[note_id]["file_path"]
        self.index[note_id] = metadata
        self._save_index()
    
        return f"✅ 笔记已更新: {metadata['title']}"
    

    #? —— 4. 搜索笔记 ————————————————————————————————————————————————————
    def _search_notes(
        self,
        query: str,
        limit: int = 10,
        note_type: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[Dict]:
        """搜索笔记

        Args:
            query: 搜索关键词
            limit: 返回数量限制
            note_type: 按类型过滤(可选)
            tags: 按标签过滤(可选)

        Returns:
            List[Dict]: 匹配的笔记列表
        """
        results = []
        query_lower = query.lower()

        for note_id, metadata in self.index.items():
            # 类型过滤
            if note_type and metadata.get("type") != note_type:
                continue

            # 标签过滤
            if tags:
                note_tags = set(metadata.get("tags", []))
                if not note_tags.intersection(tags):  # intersection 检查是否有公共标签
                    continue

            # 读取笔记内容
            try:
                note = self._read_note(note_id)
                content = note["content"]
                title = metadata.get("title", "")

                # 在标题和内容中搜索
                if query_lower in title.lower() or query_lower in content.lower():
                    results.append({
                        "note_id": note_id,
                        "title": title,
                        "type": metadata.get("type"),
                        "tags": metadata.get("tags", []),
                        "content": content,
                        "updated_at": metadata.get("updated_at")
                    })
            except Exception as e:
                print(f"[WARNING] 读取笔记 {note_id} 失败: {e}")
                continue

        # 按更新时间排序
        results.sort(key=lambda x: x["updated_at"], reverse=True)

        return results[:limit]


    #? —— 5. 列出笔记 ————————————————————————————————————————————————————
    def _list_notes(
        self,
        note_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 20
    ) -> List[Dict]:
        """列出笔记(按更新时间倒序)

        Args:
            note_type: 按类型过滤(可选)
            tags: 按标签过滤(可选)
            limit: 返回数量限制

        Returns:
            List[Dict]: 笔记元数据列表
        """
        results = []

        for note_id, metadata in self.index.items():
            # 类型过滤
            if note_type and metadata.get("type") != note_type:
                continue

            # 标签过滤
            if tags:
                note_tags = set(metadata.get("tags", []))
                if not note_tags.intersection(tags):
                    continue

            results.append(metadata)

        # 按更新时间排序
        results.sort(key=lambda x: x.get("updated_at", ""), reverse=True)

        return results[:limit]


    #? —— 6. 笔记摘要 ————————————————————————————————————————————————————
    def _summary(self) -> Dict[str, Any]:
        """生成笔记摘要统计
    
        Returns:
            Dict: 统计信息
        """
        total_count = len(self.index)
    
        # 按类型统计
        type_counts = {}
        for metadata in self.index.values():
            note_type = metadata.get("type", "general")
            type_counts[note_type] = type_counts.get(note_type, 0) + 1
    
        # 最近更新的笔记
        recent_notes = sorted(
            self.index.values(),
            key=lambda x: x.get("updated_at", ""),
            reverse=True
        )[:5]
    
        return {
            "total_notes": total_count,
            "type_distribution": type_counts,
            "recent_notes": [
                {
                    "id": note.get("id", ""),
                    "title": note.get("title", ""),
                    "type": note.get("type"),
                    "updated_at": note.get("updated_at")
                }
                for note in recent_notes
            ]
        }

    #? —— 7. 删除笔记 ————————————————————————————————————————————————————
    def _delete_note(self, note_id: str) -> str:
        """删除笔记
    
        Args:
            note_id: 笔记ID
    
        Returns:
            str: 操作结果消息
        """
        if note_id not in self.index:
            raise ValueError(f"笔记不存在: {note_id}")
    
        # 1. 删除文件
        file_path = self.index[note_id]["file_path"]
        if os.path.exists(file_path):
            os.remove(file_path)
    
        # 2. 从索引中移除
        title = self.index[note_id].get("title", note_id)
        del self.index[note_id]
        self._save_index()
    
        return f"✅ 笔记已删除: {title}"
