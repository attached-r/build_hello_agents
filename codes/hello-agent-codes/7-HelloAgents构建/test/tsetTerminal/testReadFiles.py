"""
测试 TerminalTool 的文件读取功能（Windows 兼容版）。

测试范围:
  1. type 读取小文件
  2. type 读取嵌套子目录中的文件（相对路径）
  3. cd 导航后读取文件
  4. 安全拦截: 读取 workspace 之外的路径

Windows 说明:
  - 用 type 代替 cat（已在 TerminalTool 白名单中添加 type）
  - 测试文件使用系统编码写入（Windows 中文 = GBK），确保 type 输出可正确解码
"""

import sys
import os
import locale

# 将项目根目录加入模块搜索路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from hello_agents.tools.builtin.terminal_tool import TerminalTool

# 系统编码: Windows 中文 = gbk, Linux/Mac = utf-8
SYS_ENCODING = locale.getpreferredencoding()


def setup_test_data(workspace: str):
    """在 workspace 中创建测试数据文件（使用系统编码写入）。"""
    # ── 小文件: readme.txt ──
    with open(os.path.join(workspace, "readme.txt"), "w", encoding=SYS_ENCODING) as f:
        f.write("Hello Agents!\n这是 TerminalTool 的读取测试文件。\n")

    # ── 嵌套子目录中的文件 ──
    data_dir = os.path.join(workspace, "test_data")
    os.makedirs(data_dir, exist_ok=True)
    with open(os.path.join(data_dir, "nested.txt"), "w", encoding=SYS_ENCODING) as f:
        f.write("这是嵌套在子目录中的文件。\n路径: test_data/nested.txt\n")

    print(f"  ✅ 测试文件已创建（编码: {SYS_ENCODING}）:")
    for root, dirs, files in os.walk(workspace):
        for f in files:
            if f.endswith(".py"):
                continue
            rel = os.path.relpath(os.path.join(root, f), workspace)
            print(f"     - {rel}")


def test_type_read_file(terminal):
    """测试 1: type 读取小文件。"""
    print("\n" + "-" * 50)
    print("测试 1: type 命令读取文件")
    print("-" * 50)

    result = terminal.run({"command": "type readme.txt", "description": "查看 readme"})
    print(result)

    assert "Hello Agents!" in result, "❌ 没有读到 Hello Agents!"
    assert "成功" in result, "❌ 命令执行失败"
    print("✅ 测试 1 通过")


def test_type_nested_file(terminal):
    """测试 2: type 读取子目录中的文件（相对路径）。"""
    print("\n" + "-" * 50)
    print("测试 2: type 读取子目录文件")
    print("-" * 50)

    result = terminal.run({
        "command": "type test_data/nested.txt",
        "description": "查看子目录中的文件",
    })
    print(result)

    assert "嵌套在子目录中" in result, "❌ 没有读到嵌套文件内容"
    print("✅ 测试 2 通过")


def test_read_via_cd_navigation(terminal):
    """测试 3: cd 进入子目录后再读取文件。"""
    print("\n" + "-" * 50)
    print("测试 3: cd 导航后读取文件")
    print("-" * 50)

    # Step 1: cd 进入 test_data
    step1 = terminal.run({"command": "cd test_data", "description": "进入 test_data 目录"})
    first_line = step1.split(chr(10))[0]
    print(f"  Step1: {first_line}")
    assert "test_data" in step1, "❌ cd 应该进入 test_data 目录"

    # Step 2: 在 test_data 中 type nested.txt
    step2 = terminal.run({
        "command": "type nested.txt",
        "description": "在 test_data 中查看 nested.txt",
    })
    print(f"  Step2:\n{step2}")
    assert "嵌套在子目录中" in step2, "❌ 应该读到 nested.txt 内容"

    # Step 3: cd .. 返回上级
    step3 = terminal.run({"command": "cd ..", "description": "返回上级"})
    print(f"  Step3: {step3.split(chr(10))[0]}")

    # Step 4: 确认回到上级后仍能读取原文件
    step4 = terminal.run({"command": "type readme.txt", "description": "确认返回后能读"})
    assert "Hello Agents!" in step4, "❌ 返回上级后读取失败"

    print("✅ 测试 3 通过")


def test_block_outside_workspace(terminal):
    """测试 4: 尝试读取 workspace 之外的文件——应该被拦截。"""
    print("\n" + "-" * 50)
    print("测试 4: 拦截越界路径读取")
    print("-" * 50)

    result = terminal.run({
        "command": "type C:/Windows/System32/drivers/etc/hosts",
        "description": "尝试越界读取",
    })
    print(result)

    # 应该被安全机制拦截
    is_blocked = (
        "安全校验失败" in result
        or "超出工作目录沙箱" in result
        or "禁止关键词" in result
        or "不在白名单" in result
    )
    assert is_blocked, "❌ 越界路径应该被拦截"
    print("✅ 测试 4 通过")


def cleanup(workspace: str):
    """清理测试数据。"""
    for f in ["readme.txt"]:
        path = os.path.join(workspace, f)
        if os.path.exists(path):
            os.remove(path)
    nested = os.path.join(workspace, "test_data", "nested.txt")
    if os.path.exists(nested):
        os.remove(nested)
    data_dir = os.path.join(workspace, "test_data")
    if os.path.exists(data_dir):
        os.rmdir(data_dir)


if __name__ == "__main__":
    print("=" * 50)
    print("TerminalTool 文件读取功能测试 (Windows)")
    print("=" * 50)

    # ── workspace = 当前测试目录本身 ──
    workspace = os.path.dirname(os.path.abspath(__file__))
    print(f"\n📂 Workspace: {workspace}")

    # 准备测试数据
    setup_test_data(workspace)

    # 创建 TerminalTool 实例
    terminal = TerminalTool(
        workspace=workspace,
        timeout=10,
        max_output_chars=2000,
        allow_cd=True,
    )

    try:
        test_type_read_file(terminal)
        test_type_nested_file(terminal)
        test_read_via_cd_navigation(terminal)
        test_block_outside_workspace(terminal)

    finally:
        cleanup(workspace)

    print("\n" + "=" * 50)
    print("🎉 所有测试通过！")
    print("=" * 50)
