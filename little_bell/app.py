"""小铃铛 - 主入口
架构：rumps 菜单栏 (主线程 AppKit) + Flask server (后台线程) + Bark 推送
宠物浮窗使用 PyObjC 原生窗口，与 rumps 共享同一 AppKit RunLoop。
"""
import sys
import threading
import logging
import signal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("little-bell")


def main():
    from pathlib import Path
    from little_bell.config import load_config
    from little_bell.notifier import BarkNotifier
    from little_bell.server import init_server, run_server
    from little_bell.menubar import LittleBellMenubar

    config = load_config()
    notifier = BarkNotifier(config)

    if not notifier.is_configured:
        logger.warning("Bark 未配置 device_key，推送功能不可用。请编辑 config.yaml")

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

    # Init server
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
    pet = None
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
    # rumps.App.run() drives the AppKit main loop
    menubar_app.run()


if __name__ == "__main__":
    main()
