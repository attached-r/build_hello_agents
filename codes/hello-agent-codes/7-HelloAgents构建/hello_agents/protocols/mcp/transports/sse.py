"""
MCP SSE 传输 — 通过 HTTP/SSE 流式协议连接远程 MCP 服务器。

SSE 协议流程:
  1. 客户端 GET 请求 SSE 端点 → 建立持久连接
  2. 服务器发送 event: endpoint / data: <消息 URL>
  3. 客户端通过 POST 发送 JSON-RPC 消息到消息 URL
  4. 服务器通过 SSE 推送 JSON-RPC 响应消息

用法:
    config = SSEConfig(
        url="http://localhost:8000/mcp",
        headers={"Authorization": "Bearer xxx"},
        timeout=60.0,
    )
    transport = SSETransport(config)
    async with transport:
        await transport.send({"jsonrpc": "2.0", "method": "tools/list", "id": 1})
        response = await transport.recv()
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import httpx


@dataclass
class SSEConfig:
    """SSE 传输配置

    Attributes:
        url: SSE 端点地址（如 http://localhost:8000/mcp）
        headers: 自定义 HTTP 请求头
        timeout: HTTP 超时（秒）
    """

    url: str
    headers: Dict[str, str] = field(default_factory=dict)
    timeout: float = 60.0


class SSETransport:
    """MCP SSE 传输层

    通过 HTTP SSE 连接到远程 MCP 服务器，支持:
    - 自动解析 ``event: endpoint`` 获取消息 POST URL
    - 流式接收 JSON-RPC 消息
    - 发送 JSON-RPC 请求
    - 自定义请求头、超时控制

    与 ``fastmcp.Client`` 兼容，可作为传输层直接传入::

        transport = SSETransport(SSEConfig(url="http://localhost:8000/mcp"))
        client = fastmcp.Client(transport)
        await client.__aenter__()
    """

    def __init__(self, config: SSEConfig):
        self._config = config
        self._client: Optional[httpx.AsyncClient] = None
        self._response: Optional[httpx.Response] = None
        self._message_url: Optional[str] = None
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._recv_task: Optional[asyncio.Task] = None
        self._endpoint_event: asyncio.Event = asyncio.Event()
        self._closed: bool = False

    # ── 上下文管理器 ──────────────────────────────────────────────

    async def __aenter__(self) -> "SSETransport":
        await self.connect()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    # ── 连接生命周期 ──────────────────────────────────────────────

    async def connect(self) -> None:
        """建立 SSE 连接，等待服务器下发 ``endpoint`` 事件。"""
        self._client = httpx.AsyncClient(
            headers=self._config.headers,
            timeout=self._config.timeout,
        )

        # 发起 SSE 流式请求（不立即进入上下文，由 _read_sse_loop 接管）
        self._response = await self._client.stream("GET", self._config.url)

        # 后台解析 SSE 事件
        self._recv_task = asyncio.create_task(self._read_sse_loop())

        # 等待 endpoint 事件（带超时）
        try:
            await asyncio.wait_for(
                self._endpoint_event.wait(),
                timeout=self._config.timeout,
            )
        except asyncio.TimeoutError:
            await self.close()
            raise RuntimeError(
                f"SSE 连接超时: 未收到服务器 {self._config.url} 的 endpoint 事件"
            )

    async def close(self) -> None:
        """关闭 SSE 连接，释放资源。"""
        self._closed = True
        if self._recv_task is not None and not self._recv_task.done():
            self._recv_task.cancel()
            try:
                await self._recv_task
            except (asyncio.CancelledError, Exception):
                pass
            self._recv_task = None
        if self._response is not None:
            try:
                await self._response.aclose()
            except Exception:
                pass
            self._response = None
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    # ── SSE 解析 ─────────────────────────────────────────────────

    async def _read_sse_loop(self) -> None:
        """后台协程: 持续读取 HTTP 响应体，按 SSE 协议解析事件。"""
        buffer = ""
        try:
            async with self._response:  # type: ignore[union-attr]
                async for chunk in self._response.aiter_text():
                    if self._closed:
                        break
                    buffer += chunk
                    # 按 \\n\\n 分割完整 SSE 事件
                    while "\n\n" in buffer:
                        raw_event, buffer = buffer.split("\n\n", 1)
                        self._handle_sse_event(raw_event)
        except Exception as exc:
            if not self._closed:
                await self._message_queue.put(f"__error__:{exc}")

    def _handle_sse_event(self, raw: str) -> None:
        """解析单条 SSE 事件并分发。"""
        event_type = ""
        data = ""
        for line in raw.strip().split("\n"):
            if line.startswith("event:"):
                event_type = line[6:].strip()
            elif line.startswith("data:"):
                data = line[5:].strip()

        if event_type == "endpoint" and data:
            self._message_url = data
            self._endpoint_event.set()
        elif event_type == "message" and data:
            self._message_queue.put_nowait(data)

    # ── 消息收发接口（MCP Transport 协议） ────────────────────────

    async def send(self, message: Any) -> None:
        """发送 JSON-RPC 消息。

        Args:
            message: JSON-RPC 消息，支持 str / dict / JSONRPCMessage 等形式

        Raises:
            RuntimeError: 未收到 endpoint 事件或连接未建立
            httpx.HTTPStatusError: POST 请求失败
        """
        if self._message_url is None:
            raise RuntimeError("尚未收到 endpoint 事件，无法发送消息")
        if self._client is None:
            raise RuntimeError("传输层未连接")

        # 序列化消息
        if hasattr(message, "to_json"):
            payload = json.dumps(message.to_json())
        elif isinstance(message, (dict, list)):
            payload = json.dumps(message)
        else:
            payload = str(message)

        # POST 到消息端点
        response = await self._client.post(
            self._message_url,
            content=payload,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()

        # 部分 MCP 服务器会在 POST 响应中同步返回 JSON-RPC 结果
        body = response.text.strip()
        if body:
            try:
                parsed = json.loads(body)
                if isinstance(parsed, dict) and (
                    "result" in parsed or "error" in parsed
                ):
                    self._message_queue.put_nowait(body)
            except json.JSONDecodeError:
                pass

    async def recv(self) -> str:
        """接收下一条 JSON-RPC 消息。

        Returns:
            JSON-RPC 消息字符串（调用方应根据 MCP SDK 自行反序列化）

        Raises:
            RuntimeError: 传输层已关闭或发生错误
        """
        if self._closed:
            raise RuntimeError("传输层已关闭")

        message = await self._message_queue.get()

        if isinstance(message, str) and message.startswith("__error__:"):
            raise RuntimeError(message[len("__error__:"):])

        return message

    # ── 便捷属性 ─────────────────────────────────────────────────

    @property
    def connected(self) -> bool:
        """连接是否已建立。"""
        return (
            self._client is not None
            and self._message_url is not None
            and not self._closed
        )
