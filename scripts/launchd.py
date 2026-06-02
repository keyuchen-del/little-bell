#!/usr/bin/env python3
"""管理 macOS launchd 开机自启。

Usage:
    uv run python scripts/launchd.py install   # 注册开机自启
    uv run python scripts/launchd.py remove    # 取消开机自启
    uv run python scripts/launchd.py status    # 查看状态
"""
import subprocess
import sys
from pathlib import Path

LABEL = "com.littlebell.agent"
PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
PROJECT_DIR = Path(__file__).parent.parent.resolve()


def get_plist_content():
    uv_path = subprocess.run(["which", "uv"], capture_output=True, text=True).stdout.strip()
    if not uv_path:
        uv_path = "/opt/homebrew/bin/uv"

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{uv_path}</string>
        <string>run</string>
        <string>--project</string>
        <string>{PROJECT_DIR}</string>
        <string>python</string>
        <string>-m</string>
        <string>little_bell</string>
    </array>
    <key>WorkingDirectory</key>
    <string>{PROJECT_DIR}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>
    <key>StandardOutPath</key>
    <string>{Path.home()}/Library/Logs/little-bell.log</string>
    <key>StandardErrorPath</key>
    <string>{Path.home()}/Library/Logs/little-bell.log</string>
    <key>ProcessType</key>
    <string>Interactive</string>
</dict>
</plist>
"""


def install():
    PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    PLIST_PATH.write_text(get_plist_content())
    subprocess.run(["launchctl", "load", str(PLIST_PATH)], check=True)
    print(f"✅ 开机自启已注册")
    print(f"   plist: {PLIST_PATH}")
    print(f"   日志:  ~/Library/Logs/little-bell.log")


def remove():
    if PLIST_PATH.exists():
        subprocess.run(["launchctl", "unload", str(PLIST_PATH)], check=False)
        PLIST_PATH.unlink()
        print("✅ 开机自启已移除")
    else:
        print("未注册开机自启")


def status():
    if PLIST_PATH.exists():
        result = subprocess.run(
            ["launchctl", "list", LABEL],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            print(f"✅ 已注册且运行中")
        else:
            print(f"⚠️  已注册但未运行 (可能已崩溃)")
        print(f"   plist: {PLIST_PATH}")
    else:
        print("❌ 未注册开机自启")
        print(f"   注册: uv run python scripts/launchd.py install")


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("install", "remove", "status"):
        print(__doc__)
        return

    cmd = sys.argv[1]
    {"install": install, "remove": remove, "status": status}[cmd]()


if __name__ == "__main__":
    main()
