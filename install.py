#!/usr/bin/env python3
"""小铃铛安装脚本 - 配置 Claude Code hooks 并验证连通性."""
import json
import os
import sys
import stat
import shutil
from pathlib import Path

HOOK_SCRIPT = Path(__file__).parent / "hooks" / "claude_code_hook.sh"
CLAUDE_SETTINGS = Path.home() / ".claude" / "settings.json"
HOOK_EVENTS = ["Stop", "Notification"]


def make_hook_executable():
    hook_path = HOOK_SCRIPT.resolve()
    hook_path.chmod(hook_path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    print(f"  [OK] Hook 脚本已设为可执行: {hook_path}")
    return str(hook_path)


def inject_claude_hooks(hook_path):
    if not CLAUDE_SETTINGS.exists():
        print(f"  [SKIP] Claude Code 配置文件不存在: {CLAUDE_SETTINGS}")
        return False

    # Backup
    backup_path = CLAUDE_SETTINGS.with_suffix(".json.little-bell-backup")
    shutil.copy2(CLAUDE_SETTINGS, backup_path)
    print(f"  [OK] 已备份原配置: {backup_path}")

    with open(CLAUDE_SETTINGS, "r", encoding="utf-8") as f:
        settings = json.load(f)

    hooks = settings.setdefault("hooks", {})
    modified = False

    for event in HOOK_EVENTS:
        event_hooks = hooks.setdefault(event, [])

        # Check if already installed
        already_installed = any(
            "little-bell" in str(h.get("hooks", [{}])[0].get("command", ""))
            if isinstance(h, dict)
            else False
            for h in event_hooks
        )

        if already_installed:
            print(f"  [SKIP] {event} hook 已存在")
            continue

        hook_entry = {
            "hooks": [
                {
                    "type": "command",
                    "command": f'"{hook_path}" {event}',
                    "timeout": 3,
                    "async": True,
                }
            ]
        }
        event_hooks.append(hook_entry)
        modified = True
        print(f"  [OK] 已注入 {event} hook")

    if modified:
        with open(CLAUDE_SETTINGS, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        print(f"  [OK] 已更新 Claude Code 配置")
    return modified


def setup_bark():
    config_path = Path(__file__).parent / "config.yaml"
    print("\n--- Bark 推送配置 ---")
    print("请在 iOS App Store 下载 Bark 应用并获取 Device Key")
    print("格式示例: https://api.day.app/XXXXXXXXXXXXXXXX")

    device_key = input("\n请输入你的 Bark Device Key (留空跳过): ").strip()
    if device_key:
        import yaml
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        config["bark"]["device_key"] = device_key
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
        print(f"  [OK] Bark Device Key 已保存")
        return True
    else:
        print("  [SKIP] 稍后可在 config.yaml 中配置")
        return False


def test_connection():
    import requests
    try:
        resp = requests.get("http://127.0.0.1:6789/health", timeout=2)
        if resp.status_code == 200:
            print("  [OK] 小铃铛服务运行正常")
            return True
    except Exception:
        pass
    print("  [INFO] 小铃铛服务未运行 (请先启动: python -m little_bell.app)")
    return False


def main():
    print("=" * 50)
    print("  小铃铛 (Little Bell) - 安装向导")
    print("=" * 50)

    print("\n[1/4] 设置 Hook 脚本权限...")
    hook_path = make_hook_executable()

    print("\n[2/4] 注入 Claude Code Hooks...")
    inject_claude_hooks(hook_path)

    print("\n[3/4] 配置 Bark 推送...")
    setup_bark()

    print("\n[4/4] 检查服务连通性...")
    test_connection()

    print("\n" + "=" * 50)
    print("  安装完成!")
    print("  启动命令: cd little-bell && python -m little_bell.app")
    print("=" * 50)


if __name__ == "__main__":
    main()
