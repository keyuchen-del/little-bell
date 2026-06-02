#!/usr/bin/env python3
"""小铃铛安装/卸载脚本。

Usage:
    uv run python install.py                    # 交互式安装
    uv run python install.py --yes              # 非交互，跳过 Bark 配置
    uv run python install.py --bark-key KEY     # 非交互 + 自动配置 Bark
    uv run python install.py --remove           # 卸载：移除 Claude Code hooks
    uv run python install.py --status           # 查看当前安装状态
"""
import argparse
import json
import shutil
import stat
import sys
from pathlib import Path

HOOK_SCRIPT = Path(__file__).parent / "hooks" / "claude_code_hook.sh"
CLAUDE_SETTINGS = Path.home() / ".claude" / "settings.json"
CONFIG_PATH = Path(__file__).parent / "config.yaml"
EXAMPLE_CONFIG = Path(__file__).parent / "config.example.yaml"
HOOK_EVENTS = ["Stop", "Notification"]
HOOK_MARKER = "little-bell"


def make_hook_executable():
    hook_path = HOOK_SCRIPT.resolve()
    hook_path.chmod(hook_path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    print(f"  [OK] Hook 脚本: {hook_path}")
    return str(hook_path)


def inject_claude_hooks(hook_path):
    if not CLAUDE_SETTINGS.exists():
        print(f"  [SKIP] Claude Code 未安装 ({CLAUDE_SETTINGS} 不存在)")
        return False

    backup_path = CLAUDE_SETTINGS.with_suffix(".json.little-bell-backup")
    shutil.copy2(CLAUDE_SETTINGS, backup_path)

    with open(CLAUDE_SETTINGS, "r", encoding="utf-8") as f:
        settings = json.load(f)

    hooks = settings.setdefault("hooks", {})
    modified = False

    for event in HOOK_EVENTS:
        event_hooks = hooks.setdefault(event, [])

        already = any(
            HOOK_MARKER in str(h.get("hooks", [{}])[0].get("command", ""))
            for h in event_hooks if isinstance(h, dict)
        )
        if already:
            print(f"  [SKIP] {event} hook 已存在")
            continue

        event_hooks.append({
            "hooks": [{
                "type": "command",
                "command": f'"{hook_path}" {event}',
                "timeout": 3,
                "async": True,
            }]
        })
        modified = True
        print(f"  [OK] 注入 {event} hook")

    if modified:
        with open(CLAUDE_SETTINGS, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
    else:
        backup_path.unlink(missing_ok=True)

    return modified


def remove_claude_hooks():
    if not CLAUDE_SETTINGS.exists():
        print("  [SKIP] Claude Code 未安装")
        return False

    with open(CLAUDE_SETTINGS, "r", encoding="utf-8") as f:
        settings = json.load(f)

    hooks = settings.get("hooks", {})
    modified = False

    for event in HOOK_EVENTS:
        event_hooks = hooks.get(event, [])
        original_len = len(event_hooks)
        hooks[event] = [
            h for h in event_hooks
            if not (isinstance(h, dict) and HOOK_MARKER in str(h.get("hooks", [{}])[0].get("command", "")))
        ]
        if len(hooks[event]) < original_len:
            modified = True
            print(f"  [OK] 移除 {event} hook")

    if modified:
        with open(CLAUDE_SETTINGS, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        print("  [OK] Claude Code 配置已更新")
    else:
        print("  [INFO] 未找到小铃铛 hook")
    return modified


def setup_config(bark_key=None):
    if not CONFIG_PATH.exists() and EXAMPLE_CONFIG.exists():
        shutil.copy2(EXAMPLE_CONFIG, CONFIG_PATH)
        print(f"  [OK] 已创建 config.yaml")

    if bark_key:
        import yaml
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        config.setdefault("bark", {})["device_key"] = bark_key
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
        print(f"  [OK] Bark Device Key 已配置")


def show_status():
    print("--- 小铃铛安装状态 ---\n")

    # Config
    if CONFIG_PATH.exists():
        import yaml
        with open(CONFIG_PATH, "r") as f:
            config = yaml.safe_load(f)
        bark_key = config.get("bark", {}).get("device_key", "")
        webhook_url = config.get("webhook", {}).get("url", "")
        print(f"  config.yaml: 存在")
        print(f"  Bark: {'已配置' if bark_key else '未配置'}")
        print(f"  Webhook: {'已配置' if webhook_url else '未配置'}")
    else:
        print(f"  config.yaml: 不存在 (将自动从 example 创建)")

    # Hooks
    print()
    if CLAUDE_SETTINGS.exists():
        with open(CLAUDE_SETTINGS, "r") as f:
            settings = json.load(f)
        hooks = settings.get("hooks", {})
        for event in HOOK_EVENTS:
            installed = any(
                HOOK_MARKER in str(h.get("hooks", [{}])[0].get("command", ""))
                for h in hooks.get(event, []) if isinstance(h, dict)
            )
            status = "✅ 已安装" if installed else "❌ 未安装"
            print(f"  Claude Code {event} hook: {status}")
    else:
        print("  Claude Code: 未安装")

    # Server
    print()
    try:
        import requests
        r = requests.get("http://127.0.0.1:6789/health", timeout=1)
        if r.status_code == 200:
            print("  服务状态: ✅ 运行中")
        else:
            print("  服务状态: ❌ 未运行")
    except Exception:
        print("  服务状态: ❌ 未运行")


def main():
    parser = argparse.ArgumentParser(description="小铃铛 - 安装/卸载工具")
    parser.add_argument("--yes", "-y", action="store_true", help="非交互模式，跳过所有确认")
    parser.add_argument("--bark-key", type=str, help="直接配置 Bark Device Key")
    parser.add_argument("--remove", action="store_true", help="卸载：移除 Claude Code hooks")
    parser.add_argument("--status", action="store_true", help="查看安装状态")
    args = parser.parse_args()

    if args.status:
        show_status()
        return

    if args.remove:
        print("=== 小铃铛卸载 ===\n")
        print("[1/1] 移除 Claude Code Hooks...")
        remove_claude_hooks()
        print("\n卸载完成。config.yaml 保留未删除。")
        return

    # Install
    print("=" * 50)
    print("  小铃铛 (Little Bell) - 安装")
    print("=" * 50)

    print("\n[1/3] 配置 Hook 脚本...")
    hook_path = make_hook_executable()

    print("\n[2/3] 注入 Claude Code Hooks...")
    inject_claude_hooks(hook_path)

    print("\n[3/3] 配置推送通道...")
    if args.bark_key:
        setup_config(bark_key=args.bark_key)
    elif args.yes:
        setup_config()
        print("  [INFO] 跳过 Bark 配置 (可稍后编辑 config.yaml)")
    else:
        setup_config()
        print("\n  如需配置 Bark 手机推送，请编辑 config.yaml:")
        print("  打开 Bark App → 复制首页 URL 中的 Device Key → 填入 bark.device_key")
        print()
        key = input("  现在输入 Bark Device Key (留空跳过): ").strip()
        if key:
            setup_config(bark_key=key)

    print("\n" + "=" * 50)
    print("  安装完成!")
    print("  启动: uv run python -m little_bell")
    print("  测试: uv run python -m little_bell --test")
    print("  状态: uv run python install.py --status")
    print("=" * 50)


if __name__ == "__main__":
    main()
