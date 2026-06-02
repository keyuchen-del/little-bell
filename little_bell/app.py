"""小铃铛 - 主入口

Usage:
    uv run python -m little_bell              # 正常启动
    uv run python -m little_bell --test       # 发送测试通知验证推送
    uv run python -m little_bell --no-pet     # 不显示桌面宠物
    uv run python -m little_bell --port 7890  # 指定服务端口
"""
import sys
import argparse
import threading
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("little-bell")


def send_test_notification(config):
    """发送一条测试通知到所有已配置的通道。"""
    from little_bell.notifier import NotifierManager

    notifier = NotifierManager(config)
    channels = notifier.active_channels
    print(f"已启用通道: {', '.join(channels) if channels else '(仅 macOS 通知)'}")
    print("发送测试通知...")

    ok = notifier.send("stop", detail="小铃铛测试 — 如果你收到了说明配置正确!")
    if ok:
        print("✅ 推送成功！检查你的通知。")
    else:
        print("❌ 推送失败。请检查 config.yaml 配置。")
    return ok


def main():
    parser = argparse.ArgumentParser(description="小铃铛 - AI Agent 等待通知推送")
    parser.add_argument("--test", action="store_true", help="发送测试通知并退出")
    parser.add_argument("--no-pet", action="store_true", help="不显示桌面宠物")
    parser.add_argument("--port", type=int, help="指定 HTTP 服务端口 (默认 6789)")
    parser.add_argument("--config", type=str, help="指定配置文件路径")
    args = parser.parse_args()

    from pathlib import Path
    from little_bell.config import load_config
    from little_bell.notifier import NotifierManager
    from little_bell.server import init_server, run_server
    from little_bell.menubar import LittleBellMenubar

    config = load_config(args.config)

    if args.port:
        config["server"]["port"] = args.port
    if args.no_pet:
        config["pet"]["enabled"] = False

    # --test mode: send notification and exit
    if args.test:
        send_test_notification(config)
        return

    notifier = NotifierManager(config)
    channels = notifier.active_channels
    logger.info(f"推送通道: {', '.join(channels) if channels else '(仅 macOS 通知)'}")

    # Generate assets if missing
    assets_dir = Path(__file__).parent / "assets"
    if not (assets_dir / "bell.png").exists():
        logger.info("首次启动，生成图标资源...")
        from little_bell.gen_assets import gen_menubar_icons, gen_pet_sprites
        gen_menubar_icons()
        gen_pet_sprites()

    # Create menubar app
    menubar_app = LittleBellMenubar(config, notifier)

    def on_event(event_record):
        menubar_app.on_event(event_record)

    init_server(notifier, on_event_callback=on_event)

    # Start Flask in background thread
    server_host = config["server"]["host"]
    server_port = config["server"]["port"]
    server_thread = threading.Thread(
        target=run_server,
        args=(server_host, server_port),
        daemon=True,
    )
    server_thread.start()
    logger.info(f"HTTP Server 启动在 {server_host}:{server_port}")

    # Start pet window if enabled
    if config["pet"]["enabled"]:
        try:
            from little_bell.pet_cocoa import CocoaPet
            from PyObjCTools import AppHelper
            pet = CocoaPet(config)
            pet.show()
            logger.info("浮窗宠物已显示")

            def on_event_with_pet(event_record):
                menubar_app.on_event(event_record)
                msg = event_record.get("detail") or f"{event_record['agent']}: {event_record['event']}"
                AppHelper.callAfter(pet.trigger_alert, msg)

            init_server(notifier, on_event_callback=on_event_with_pet)
        except Exception as e:
            logger.warning(f"浮窗宠物启动失败 (非关键): {e}")

    logger.info("小铃铛启动完成! 等待 Agent 事件...")
    menubar_app.run()


if __name__ == "__main__":
    main()
