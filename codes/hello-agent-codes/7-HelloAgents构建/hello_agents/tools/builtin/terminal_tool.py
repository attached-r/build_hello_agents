"""
终端工具 — 将受控的 Shell 命令封装为 Tool，供 Agent 探知文件系统。

定位与作用:
  TerminalTool 是实现 **JIT（Just-in-Time）上下文** 的关键工具。
  Agent 用受控的只读命令即时探索文件系统，而不是预先把整个代码库、
  日志目录或数据文件全部索引进 RAG。相当于 Agent 在文件系统里的
  "眼睛和双手"。

安全机制（多层防护）:
  1. 命令白名单 — 只允许只读/安全命令（cat/head/tail/grep/find/wc 等）
  2. 工作目录沙箱 — 只能访问 workspace 内部的路径
  3. 超时控制    — 防止命令卡死或长时间扫描
  4. 输出大小限制 — 防止一次返回巨量内容

术语约定:
  - "命令白名单"是指允许的命令列表，而非整个 CLI 命令字符串。
  - "工作目录沙箱"确保所有路径解析都在 workspace 内。

用法:
    tool = TerminalTool(workspace="/path/to/project")
    # 执行只读命令
    result = tool.run({"command": "ls -la", "description": "查看项目文件"})
    # 目录导航（带状态保持）
    tool.run({"command": "cd src"})       # 进入 src 子目录
    tool.run({"command": "ls"})           # 在 src 中列出文件
    tool.run({"command": "cd .."})        # 返回上一级

与 ContextBuilder 的集成:
    # 在 Agent 中将 TerminalTool 的输出转为 ContextPacket
    from hello_agents.context.builder import ContextPacket
    packet = ContextPacket(
        content=result,
        timestamp=datetime.now(),
        token_count=len(result) // 4,
        relevance_score=0.9,
        metadata={"type": "terminal", "command": "ls -la"},
    )
    builder.gather(custom_packets=[packet])
"""

import os
import shlex
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from ...tools.base import Tool, ToolParameter


# ═══════════════════════════════════════════════════════════════════════════════
# 安全常量
# ═══════════════════════════════════════════════════════════════════════════════

# 只读命令白名单 — 只允许这些命令，其余一律拒绝
# 按用途分组，便于阅读和扩展
READONLY_COMMANDS: Set[str] = {
    # ── 文件查看 ──
    "cat", "head", "tail", "less", "more", "nl",
    # ── 文件搜索与定位 ──
    "find", "grep", "rg", "ag", "ack", "locate",
    # ── 目录与属性查看 ──
    "ls", "stat", "file", "du", "df", "tree",
    # ── 文件统计 ──
    "wc", "cut", "sort", "uniq",
    # ── 文本处理（只读操作） ──
    "diff", "comm",
    # ── 时间与日期 ──
    "date",
    # ── 网络诊断（DNS/连通性检查，无副作用的） ──
    "ping", "-c",  # -c 通常与 ping 连用，用于安全限制
    "host", "nslookup",
    # ── 进程与资源查看 ──
    "ps", "top", "htop",
}

# 禁止的命令片段 — 只要命令字符串包含这些关键词，直接拒绝
# 用于防御白名单绕过尝试（如 cat + 管道到 rm）
BLOCKED_KEYWORDS: Set[str] = {
    "rm ", "rm -", "rmdir", "mkfs", "dd ", "format",
    ":(){ :|:& };:",  # fork bomb
    ">", ">>", "| tee",  # 输出重定向
    "chmod", "chown", "chattr",
    "sudo", "su ",
    "eval", "exec", "`",
    "/etc/shadow", "/etc/passwd",
    "wget ", "curl ",  # 禁止下载（不仅是上传）
}

# 默认参数
DEFAULT_TIMEOUT: int = 30        # 默认超时（秒）
DEFAULT_MAX_OUTPUT_CHARS: int = 5000   # 默认输出最大字符数
SAFE_MAX_OUTPUT_CHARS: int = 20000     # 绝对上限


# ═══════════════════════════════════════════════════════════════════════════════
# 安全验证函数
# ═══════════════════════════════════════════════════════════════════════════════

def _validate_command(command: str) -> Tuple[bool, str]:
    """验证命令是否通过安全检查。

    检查顺序:
      1. 空命令检查
      2. 禁止关键词检查（BLOCKED_KEYWORDS）
      3. 白名单检查（命令是否在 READONLY_COMMANDS 中）

    Args:
        command: 要执行的命令字符串（如 "ls -la"）

    Returns:
        (是否通过, 错误消息) — 通过时错误消息为空字符串
    """
    # 1. 空命令检查
    stripped = command.strip()
    if not stripped:
        return False, "命令不能为空"

    # 2. 禁止关键词检查（大小写不敏感）
    command_lower = stripped.lower()
    for keyword in BLOCKED_KEYWORDS:
        if keyword.lower() in command_lower:
            return False, f"命令包含禁止关键词: '{keyword}'"

    # 3. 提取基础命令名，检查白名单
    #    用 shlex.split 正确解析带引号的参数
    try:
        parts = shlex.split(stripped)
    except ValueError as e:
        return False, f"命令解析失败（引号不匹配等）: {e}"

    if not parts:
        return False, "命令解析后为空"

    base_cmd = os.path.basename(parts[0])  # 去掉路径前缀（如 /usr/bin/ls → ls）

    if base_cmd not in READONLY_COMMANDS:
        return False, (
            f"命令 '{base_cmd}' 不在白名单中。"
            f" 允许的命令: {', '.join(sorted(READONLY_COMMANDS))}"
        )

    return True, ""


def _validate_path_within_workspace(path_str: str, workspace: str) -> Tuple[bool, str]:
    """验证路径是否在 workspace 沙箱内。

    这是工作目录沙箱的第二道防线（第一道是设置 cwd=workspace）：
    检查命令中所有显式路径参数是否解析到 workspace 内。

    Args:
        path_str: 命令字符串中的路径
        workspace: 工作空间目录（绝对路径）

    Returns:
        (是否通过, 规范化后的路径或错误消息)
    """
    # 展开 ~ 和相对路径
    expanded = os.path.expanduser(path_str)
    if not os.path.isabs(expanded):
        # 相对路径以 workspace 为基准
        expanded = os.path.normpath(os.path.join(workspace, expanded))

    # 规范化（解析 .. 和符号链接）
    try:
        real = os.path.realpath(expanded)
    except (OSError, PermissionError):
        return False, f"无法解析路径: {path_str}"

    workspace_real = os.path.realpath(workspace)

    if not real.startswith(workspace_real):
        return False, (
            f"路径 '{path_str}' 在 workspace 之外 "
            f"({real} 不在 {workspace_real} 内)"
        )

    return True, real


# ═══════════════════════════════════════════════════════════════════════════════
# TerminalTool 类
# ═══════════════════════════════════════════════════════════════════════════════

class TerminalTool(Tool):
    """终端工具 — Agent 用于在文件系统中执行受控的只读命令。

    核心功能:
      1. run      统一入口，执行命令并返回结果
      2. run_raw  直接返回 (stdout, stderr, returncode) 元组
      3. validate 独立的安全校验入口

    安全机制:
      - 只读命令白名单（cat/ls/grep/find/wc 等）
      - 工作目录沙箱（只能访问 workspace 内的文件）
      - 超时控制（默认 30 秒）
      - 输出大小限制（默认 5000 字符）

    用法:
        tool = TerminalTool(workspace="/path/to/project")
        result = tool.run({"command": "ls -la", "description": "查看项目文件"})

    与 ContextBuilder 集成:
        # 在 Agent 代码中，将 TerminalTool 结果包装为 ContextPacket
        packet = ContextPacket(
            content=result,
            timestamp=datetime.now(),
            token_count=len(result) // 4,
            relevance_score=0.9,
            metadata={"type": "terminal", "command": "ls -la"},
        )
        builder.gather(custom_packets=[packet])
    """

    def __init__(
        self,
        workspace: str,
        timeout: int = DEFAULT_TIMEOUT,
        max_output_chars: int = DEFAULT_MAX_OUTPUT_CHARS,
        allow_cd: bool = True,
    ):
        """初始化 TerminalTool。

        Args:
            workspace:        工作空间目录（所有命令只能在此目录内运行）
            timeout:          命令超时秒数（默认 30 秒）
            max_output_chars: 输出最大字符数（默认 5000，绝对上限 20000）
            allow_cd:         是否允许 cd 导航命令（默认 True）
        """
        super().__init__(
            name="terminal",
            description=(
                "一个受安全限制的终端工具。Agent 可以用只读命令"
                "（如 ls/cat/grep/find/wc/head/tail）探索文件系统。"
                "所有命令在指定工作目录内执行，无法访问外部系统文件。"
                f"超时: {timeout}秒，输出上限: {max_output_chars}字符。"
                "支持 cd 命令导航目录（带状态保持）。"
            ),
        )
        # 规范化 workspace 路径
        self.workspace = os.path.realpath(os.path.normpath(workspace))
        # 当前工作目录（可被 cd 改变，始终在 workspace 内）
        self.current_dir = Path(self.workspace)
        self.allow_cd = allow_cd
        self.timeout = timeout
        # 输出上限不超绝对上限
        self.max_output_chars = min(max_output_chars, SAFE_MAX_OUTPUT_CHARS)

        # 验证 workspace 存在
        if not os.path.isdir(self.workspace):
            raise NotADirectoryError(
                f"workspace 不存在或不是目录: {self.workspace}"
            )

    #? ── 统一入口 ─────────────────────────────────────────────────────

    def run(self, parameters: Dict[str, Any]) -> str:
        """统一入口：解析参数 → 验证 → 执行 → 返回。

        Args:
            parameters: 参数字典，支持:
                - command (必需): 要执行的命令字符串
                - description (可选): 命令目的描述（仅用于日志/显示）
                - timeout (可选): 此条命令的超时覆盖
                - max_output_chars (可选): 此条命令的输出截断上限

        Returns:
            str: 命令执行结果（成功时包含 stdout，失败时包含错误信息）
        """
        command = parameters.get("command", "").strip()
        if not command:
            return "❌ 参数 'command' 不能为空"

        description = parameters.get("description", command[:60])
        timeout = parameters.get("timeout", self.timeout)
        max_output = min(
            parameters.get("max_output_chars", self.max_output_chars),
            SAFE_MAX_OUTPUT_CHARS,
        )

        # 拦截 cd 命令 — 特殊处理目录导航
        parts = shlex.split(command) if command else []
        if parts and parts[0] == "cd":
            return self._handle_cd(parts)

        # 1. 安全检查
        is_safe, error_msg = self.validate(command)
        if not is_safe:
            return f"❌ 安全校验失败: {error_msg}"

        # 2. 执行命令
        stdout, stderr, returncode = self._execute(
            command=command,
            timeout=timeout,
        )

        # 3. 格式化输出
        return self._format_output(
            command=command,
            description=description,
            stdout=stdout,
            stderr=stderr,
            returncode=returncode,
            max_output_chars=max_output,
        )

    def run_raw(
        self,
        command: str,
        timeout: Optional[int] = None,
    ) -> Tuple[str, str, int]:
        """直接执行命令并返回原始输出（跳过格式化）。

        适用于需要自行处理输出格式的调用方。

        Args:
            command: 命令字符串
            timeout: 超时秒数（None 则用实例默认值）

        Returns:
            (stdout, stderr, returncode) 元组

        Raises:
            ValueError: 安全检查未通过
            subprocess.TimeoutExpired: 命令超时
        """
        is_safe, error_msg = self.validate(command)
        if not is_safe:
            raise ValueError(f"安全校验失败: {error_msg}")

        return self._execute(command, timeout or self.timeout)

    #? ── 目录导航 ─────────────────────────────────────────────────────
    def _handle_cd(self, parts: List[str]) -> str:
        """处理 cd 命令，支持带状态的目录导航。

        智能体可以通过多步 cd 在文件系统中渐进式导航，
        每次 cd 后当前目录状态保留，后续命令在此目录执行。

        Args:
            parts: shlex.split 后的命令片段（["cd", "target"]）

        Returns:
            str: 导航结果消息
        """
        if not self.allow_cd:
            return "❌ cd 命令已禁用"

        # cd 无参数 — 返回当前目录位置
        if len(parts) < 2 or parts[1] in ("", "~"):
            return f"📂 当前目录: {self.current_dir}"

        target = parts[1]

        # ── 解析目标路径 ──────────────────────────────────────────
        if target == "..":
            new_path = self.current_dir.parent
        elif target == ".":
            new_path = self.current_dir
        elif target.startswith("/"):
            # 绝对路径 — 直接从 workspace 根开始计算
            new_path = Path(self.workspace) / target.lstrip("/")
        else:
            # 相对路径 — 基于 current_dir 解析
            new_path = (self.current_dir / target).resolve()

        # ── 安全检查：不可越出 workspace 沙箱 ─────────────────────
        try:
            new_path.relative_to(Path(self.workspace))
        except ValueError:
            return (
                f"❌ 不允许访问工作目录外的路径:\n"
                f"  目标: {new_path}\n"
                f"  限制: {self.workspace}"
            )

        # ── 存在性检查 ────────────────────────────────────────────
        if not new_path.exists():
            return f"❌ 目录不存在: {new_path}"

        if not new_path.is_dir():
            return f"❌ 不是目录: {new_path}"

        # ── 更新状态 ──────────────────────────────────────────────
        self.current_dir = new_path

        # 顺便列出目录内容，方便智能体判断下一步
        return self._format_cd_result(new_path)

    def _format_cd_result(self, path: Path) -> str:
        """cd 成功后输出目录概览。

        包含：目录路径 + 子目录/文件概要，方便 AI Agent
        在一轮中了解结构、决策下一步。

        Args:
            path: 切换到的目标目录

        Returns:
            格式化的目录概览字符串
        """
        lines: List[str] = []
        lines.append(f"📂 当前目录: {path}")
        lines.append("")

        try:
            # 收集目录内容
            items = list(path.iterdir())
            dirs = sorted([p for p in items if p.is_dir()])
            files = sorted([p for p in items if p.is_file()])

            # 目录概览
            lines.append(f"├─ 子目录 ({len(dirs)}):")
            for d in dirs:
                # 统计每个子目录中的文件数
                try:
                    file_count = sum(1 for _ in d.rglob("*") if _.is_file())
                except (PermissionError, OSError):
                    file_count = 0
                lines.append(f"│  📁 {d.name}/  ({file_count} 文件)")

            # 文件概要
            lines.append(f"├─ 文件 ({len(files)}):")
            for f in files:
                size = f.stat().st_size
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size / 1024:.1f} KB"
                else:
                    size_str = f"{size / 1024 / 1024:.1f} MB"
                lines.append(f"│  📄 {f.name}  ({size_str})")

            # 如有更多文件被截断
            total = len(dirs) + len(files)
            if total > 50:
                lines.append(f"│  ... 共 {total} 项（仅显示前 50）")

        except PermissionError:
            lines.append("  ⚠️  无权限读取目录内容")

        lines.append("")
        lines.append("💡 提示: 可继续使用 cd 深入，或用 ls/cat/head 查看文件")

        return "\n".join(lines)

    # ── 安全校验（独立入口） ─────────────────────────────────────────

    def validate(self, command: str) -> Tuple[bool, str]:
        """独立的安全校验入口。

        调用方可在执行前单独校验命令是否安全。
        这个方法是 TerminalTool 安全性的核心，供 run/run_raw 内部调用，
        也允许外部自定义执行逻辑时复用。

        Args:
            command: 待校验的命令字符串

        Returns:
            (是否安全, 错误消息)
        """
        # 第一层：通用命令验证（白名单 + 禁止关键词）
        is_valid, msg = _validate_command(command)
        if not is_valid:
            return False, msg

        # 第二层：工作目录沙箱 — 检查路径参数是否越界
        try:
            parts = shlex.split(command)
        except ValueError:
            return False, "命令解析失败"

        for part in parts:
            # 跳过以 - 开头的选项（如 -la, --color）
            if part.startswith("-"):
                continue

            # 跳过纯命令名（如 cat, grep, ls）
            if part == parts[0]:
                continue

            # 检查看起来像路径的参数
            if "/" in part or part.startswith(".") or part.startswith("~"):
                # 相对路径基于 current_dir 解析，沙箱边界仍是 workspace
                ok, _ = _validate_path_within_workspace(part, str(self.current_dir))
                if not ok:
                    # 二次验证：解析后的路径是否仍在 workspace 内
                    resolved = os.path.realpath(os.path.join(str(self.current_dir), part))
                    workspace_real = os.path.realpath(self.workspace)
                    if not resolved.startswith(workspace_real):
                        return False, (
                            f"路径 '{part}' 超出工作目录沙箱范围 "
                            f"({resolved} 不在 {workspace_real} 内)"
                        )

        return True, ""

    # ── 命令执行 ─────────────────────────────────────────────────────

    def _execute(self, command: str, timeout: int) -> Tuple[str, str, int]:
        """执行命令并返回结果。

        在 workspace 目录中执行，捕获 stdout 和 stderr。
        支持超时控制。

        Args:
            command: 命令字符串
            timeout: 超时秒数

        Returns:
            (stdout, stderr, returncode)
        """
        try:
            result = subprocess.run(
                command,
                shell=True,                     # 允许管道和重定向（受白名单保护）
                capture_output=True,            # 同时捕获 stdout 和 stderr
                cwd=str(self.current_dir),      # 工作目录（跟随 cd 导航）
                timeout=timeout,                # 超时控制
                text=True,                      # 以文本模式返回（而非 bytes）
                encoding="utf-8",               # 指定 UTF-8 编码
                errors="replace",               # 无法解码的字符用 � 替换
            )
            return (
                result.stdout or "",
                result.stderr or "",
                result.returncode,
            )

        except subprocess.TimeoutExpired as e:
            return (
                e.stdout.decode("utf-8", errors="replace") if e.stdout else "",
                f"⏱️ 命令超时（{timeout} 秒）",
                -1,
            )
        except FileNotFoundError:
            return "", f"❌ 命令未找到: {command.split()[0]}", -1
        except OSError as e:
            return "", f"❌ 系统错误: {e}", -1
        except Exception as e:
            return "", f"❌ 执行异常: {e}", -1

    # ── 输出格式化 ───────────────────────────────────────────────────

    def _format_output(
        self,
        command: str,
        description: str,
        stdout: str,
        stderr: str,
        returncode: int,
        max_output_chars: int,
    ) -> str:
        """格式化命令执行结果。

        输出结构:
          ```
          ── 终端输出 ──
          命令: <command>
          目的: <description>

          ── 标准输出 ──
          <stdout（可能截断）>

          ── 标准错误 ──
          <stderr>

          ── 执行状态 ──
          返回码: <code>
          ```

        Args:
            command:        执行的命令
            description:    命令目的
            stdout:         标准输出
            stderr:         标准错误
            returncode:     返回码
            max_output_chars: 输出截断上限

        Returns:
            格式化的输出字符串
        """
        lines: List[str] = []
        lines.append("── 终端输出 ──────────────────────────────────")
        lines.append(f"命令: {command}")
        if description:
            lines.append(f"目的: {description}")
        lines.append("")

        # ── 标准输出（带截断） ─────────────────────────────────────
        if stdout:
            truncated = False
            if len(stdout) > max_output_chars:
                stdout = stdout[:max_output_chars]
                truncated = True

            lines.append("── 标准输出 ──")
            lines.append(stdout.rstrip("\n"))
            if truncated:
                lines.append(
                    f"\n  ⚠️  输出已截断（仅显示前 {max_output_chars} 字符）"
                )

        # ── 标准错误 ───────────────────────────────────────────────
        if stderr:
            if len(stderr) > max_output_chars:
                stderr = stderr[:max_output_chars]

            lines.append("── 标准错误 ──")
            lines.append(stderr.rstrip("\n"))

        # ── 执行状态 ───────────────────────────────────────────────
        lines.append("")
        status = "✅ 成功" if returncode == 0 else f"⚠️ 返回码 {returncode}"
        lines.append(f"── 执行状态: {status} ──")

        return "\n".join(lines)

    # ── 参数 schema 定义 ────────────────────────────────────────────

    def get_parameters(self) -> List[ToolParameter]:
        """获取工具参数定义。

        供 Tool 基类的 to_openai_schema() 使用，将参数定义
        自动转为 OpenAI function calling 格式。

        Returns:
            ToolParameter 列表
        """
        return [
            ToolParameter(
                name="command",
                type="string",
                description=(
                    "要执行的终端命令（只读命令）. "
                    "支持: ls/cat/head/tail/grep/find/wc/sort/uniq 等. "
                    "支持 cd 导航目录（多步状态保持）"
                ),
            ),
            ToolParameter(
                name="description",
                type="string",
                description="此命令的执行目的（供 Agent 记录用）",
                required=False,
            ),
            ToolParameter(
                name="timeout",
                type="integer",
                description=f"命令超时秒数（默认 {DEFAULT_TIMEOUT}）",
                required=False,
            ),
        ]

    # ── 描述信息（供 Agent 理解工具能力） ──────────────────────────

    def get_capability_description(self) -> str:
        """返回 TerminalTool 的能力描述，供 Agent 系统提示词使用。

        与 ContextBuilder 的 custom_packets 配合使用时，
        这条描述帮助 LLM 理解终端输出在上下文中的含义。

        Returns:
            能力描述文本
        """
        return (
            "## 终端工具（TerminalTool）\n"
            "用于在项目工作区执行只读的 Shell 命令。\n\n"
            "### 可用命令\n"
            f"{', '.join(sorted(READONLY_COMMANDS))}\n"
            "导航: cd（带状态保持，可在多轮对话中逐步深入目录）\n\n"
            "### 使用场景\n"
            "- 目录导航: cd → 多步渐进式探索项目结构\n"
            "- 探索式导航: ls, find, head — 快速了解目录结构和关键文件\n"
            "- 数据文件分析: head, wc, cut, sort, uniq — 预览 CSV 结构和数据分布\n"
            "- 日志分析: tail, grep — 定位最近错误和错误类型\n"
            "- 代码库分析: find, grep, wc — 查找 TODO、函数定义、代码规模\n\n"
            "### 导航示例\n"
            "支持多步渐进式探索:\n"
            "  Step 1: cd src          # 进入源代码目录\n"
            "  Step 2: ls              # 查看该目录内容\n"
            "  Step 3: cd services     # 进一步深入子目录\n"
            "  Step 4: cat user_svc.py # 查看具体文件\n\n"
            "### 安全限制\n"
            f"- 工作目录沙箱: {self.workspace}\n"
            f"- 超时控制: {self.timeout}s\n"
            f"- 输出上限: {self.max_output_chars} 字符\n"
            "- 禁止修改/删除/网络下载等破坏性操作\n\n"
            "### 输出价值分流\n"
            "TerminalTool 的输出不应长期留在对话历史中:\n"
            "1. 当前轮需要的片段 → 放入 ContextBuilder 的 custom_packets\n"
            "2. 重要结论 → 写入 NoteTool\n"
            "3. 用户偏好或稳定知识 → 写入 MemoryTool\n"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 便捷工厂函数
# ═══════════════════════════════════════════════════════════════════════════════

def create_terminal_tool(
    workspace: str,
    timeout: int = DEFAULT_TIMEOUT,
    max_output_chars: int = DEFAULT_MAX_OUTPUT_CHARS,
    allow_cd: bool = True,
) -> TerminalTool:
    """创建并返回 TerminalTool 实例的便捷函数。

    用法:
        terminal_tool = create_terminal_tool("/path/to/workspace")
    """
    return TerminalTool(
        workspace=workspace,
        timeout=timeout,
        max_output_chars=max_output_chars,
        allow_cd=allow_cd,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 自测 / 演示
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import tempfile

    print("=" * 60)
    print("TerminalTool 自测")
    print("=" * 60)

    # 创建临时 workspace
    with tempfile.TemporaryDirectory() as td:
        # 创建一些测试文件
        test_file = os.path.join(td, "README.md")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("# Test Project\n\n## 概述\n这是一个测试项目。\n")

        tool = TerminalTool(workspace=td)

        # 测试 1: 合法命令
        print("\n--- 测试 1: ls 命令 ---")
        result = tool.run({"command": "ls -la", "description": "列出文件"})
        print(result)

        # 测试 2: cat 文件
        print("\n--- 测试 2: cat 命令 ---")
        result = tool.run({"command": "cat README.md", "description": "查看 README"})
        print(result)

        # 测试 3: 超出 workspace 的路径
        print("\n--- 测试 3: 拦截越界路径 ---")
        result = tool.run({"command": "cat /etc/passwd"})
        print(result)

        # 测试 4: 禁止的命令
        print("\n--- 测试 4: 拦截危险命令 ---")
        result = tool.run({"command": "rm -rf /"})
        print(result)

        # 测试 5: 空命令
        print("\n--- 测试 5: 空命令 ---")
        result = tool.run({"command": ""})
        print(result)

    print("\n" + "=" * 60)
    print("自测完成")
    print("=" * 60)
