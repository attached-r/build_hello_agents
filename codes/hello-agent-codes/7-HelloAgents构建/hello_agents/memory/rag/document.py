"""
文档处理器 — 多格式文档解析与智能分块。

支持格式:
  .txt / .md    直接 UTF-8 读取
  .pdf / .docx / .xlsx / .html / 图片  通过 MarkItDown 库转换

分块策略（三层递进）:
  1. 按标题分割（Markdown 标题层级）
  2. 长内容按段落拆分
  3. 短块合并
"""

import hashlib
import os
import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DocumentChunk:
    """文档分块的数据结构"""

    content: str
    source: str
    chunk_index: int
    heading: str = ""
    heading_level: int = 0
    metadata: dict = field(default_factory=dict)
    chunk_id: str = ""

    def __post_init__(self):
        if not self.chunk_id:
            raw = f"{self.content}:{self.source}:{self.chunk_index}"
            self.chunk_id = hashlib.md5(raw.encode()).hexdigest()[:16]


class DocumentProcessor:
    """多格式文档解析与智能分块"""

    # Markdown 标题正则
    HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

    def __init__(
        self,
        max_chunk_size: int = 1000,
        min_chunk_size: int = 200,
    ):
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size

    # ── 文档解析 ──────────────────────────────────────────────

    def parse(self, file_path: str) -> str:
        """读取文件内容为纯文本"""
        ext = os.path.splitext(file_path)[1].lower()

        if ext in (".txt", ".md"):
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()

        # MarkItDown 方式
        try:
            from markitdown import MarkItDown
            md = MarkItDown()
            result = md.convert(file_path)
            return result.text_content or ""
        except ImportError:
            raise ImportError(
                f"解析 {ext} 文件需要 MarkItDown: pip install markitdown"
            )
        except Exception as e:
            raise RuntimeError(f"文件解析失败: {file_path} — {e}")

    # ── 智能分块 ──────────────────────────────────────────────

    def chunk(self, text: str, source: str = "") -> list[DocumentChunk]:
        """
        将文本进行智能分块。

        策略：
          1. 按标题分割
          2. 长内容按段落拆分
          3. 短块合并
        """
        sections = self._split_by_headings(text)
        chunks: list[DocumentChunk] = []

        for heading_text, heading_level, body in sections:
            # 按段落拆分正文
            paragraphs = re.split(r"\n\s*\n", body.strip())
            buffer = ""
            buffer_start = 0

            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue

                # 当前段加到缓冲区后是否超长
                candidate = (buffer + "\n\n" + para).strip() if buffer else para
                if len(candidate) <= self.max_chunk_size:
                    buffer = candidate
                else:
                    # 缓冲区非空则先存
                    if buffer:
                        chunks.append(self._make_chunk(
                            buffer, source, len(chunks),
                            heading_text, heading_level,
                        ))
                        buffer = ""
                    # 段落本身超长，按字符拆分
                    if len(para) > self.max_chunk_size:
                        for i in range(0, len(para), self.max_chunk_size):
                            segment = para[i:i + self.max_chunk_size]
                            chunks.append(self._make_chunk(
                                segment, source, len(chunks),
                                heading_text, heading_level,
                            ))
                    else:
                        buffer = para

            # 剩余缓冲区
            if buffer:
                chunks.append(self._make_chunk(
                    buffer, source, len(chunks),
                    heading_text, heading_level,
                ))

        # 短块合并
        chunks = self._merge_short_chunks(chunks)
        return chunks

    # ── 内部方法 ──────────────────────────────────────────────

    def _split_by_headings(self, text: str) -> list[tuple[str, int, str]]:
        """按 Markdown 标题将文本分割为区块"""
        lines = text.split("\n")
        sections: list[tuple[str, int, str]] = []
        current_heading = ""
        current_level = 0
        current_body: list[str] = []

        for line in lines:
            m = self.HEADING_PATTERN.match(line)
            if m:
                # 保存上一区块
                if current_body:
                    sections.append((
                        current_heading, current_level,
                        "\n".join(current_body),
                    ))
                    current_body = []
                current_heading = m.group(2).strip()
                current_level = len(m.group(1))
            else:
                current_body.append(line)

        if current_body:
            sections.append((
                current_heading, current_level,
                "\n".join(current_body),
            ))

        return sections

    def _make_chunk(
        self, content: str, source: str, index: int,
        heading: str, level: int,
    ) -> DocumentChunk:
        return DocumentChunk(
            content=content.strip(),
            source=source,
            chunk_index=index,
            heading=heading,
            heading_level=level,
        )

    def _merge_short_chunks(self, chunks: list[DocumentChunk]) -> list[DocumentChunk]:
        """将低于 min_chunk_size 的相邻块合并"""
        if not chunks:
            return chunks

        merged: list[DocumentChunk] = [chunks[0]]
        for chunk in chunks[1:]:
            prev = merged[-1]
            if len(prev.content) < self.min_chunk_size:
                # 合并到上一个块
                prev.content += "\n\n" + chunk.content
                prev.metadata["merged_index"] = chunk.chunk_index
            else:
                merged.append(chunk)
        return merged
