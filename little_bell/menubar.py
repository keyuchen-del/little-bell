import rumps
import threading
from pathlib import Path
from datetime import datetime
from Foundation import NSObject
from AppKit import NSApplication
import objc

ASSETS_DIR = Path(__file__).parent / "assets"


class LittleBellMenubar(rumps.App):
    def __init__(self, config, notifier):
        icon_path = str(ASSETS_DIR / "bell.png")
        super().__init__("小铃铛", icon=icon_path, quit_button="退出")
        self.config = config
        self.notifier = notifier
        self._alert_icon = str(ASSETS_DIR / "bell_alert.png")
        self._normal_icon = icon_path
        self._pending_count = 0
        self._event_texts = []
        self._reset_timer = None
        self._push_enabled = True

        self.status_item = rumps.MenuItem("状态: 监听中...")
        self.events_menu = rumps.MenuItem("最近事件")
        self.events_menu.add(rumps.MenuItem("(暂无事件)"))
        channels = notifier.active_channels if hasattr(notifier, 'active_channels') else []
        self.bark_status = rumps.MenuItem(
            f"通道: {', '.join(channels) if channels else '仅 macOS 通知'}"
        )
        self.toggle_item = rumps.MenuItem("暂停推送", callback=self.toggle_push)

        self.menu = [
            self.status_item,
            None,
            self.events_menu,
            None,
            self.bark_status,
            self.toggle_item,
        ]

    def on_event(self, event_record):
        self._pending_count += 1

        event_text = f"[{event_record['agent']}] {event_record['event']}"
        if event_record.get("detail"):
            event_text += f": {event_record['detail'][:40]}"
        time_str = datetime.now().strftime("%H:%M:%S")
        self._event_texts.insert(0, f"{time_str} {event_text}")
        self._event_texts = self._event_texts[:10]

        # Schedule UI update on main thread
        self._schedule_main_thread(self._update_ui)

    def _schedule_main_thread(self, func):
        """Schedule a function to run on the main AppKit thread."""
        try:
            from PyObjCTools import AppHelper
            AppHelper.callAfter(func)
        except Exception:
            func()

    def _update_ui(self):
        try:
            self.icon = self._alert_icon
            self.title = f" {self._pending_count}"
        except Exception:
            pass

        if self._reset_timer:
            self._reset_timer.cancel()
        self._reset_timer = threading.Timer(10.0, self._reset_icon_safe)
        self._reset_timer.daemon = True
        self._reset_timer.start()

    def _reset_icon_safe(self):
        self._schedule_main_thread(self._reset_icon)

    def _reset_icon(self):
        self._pending_count = 0
        try:
            self.icon = self._normal_icon
            self.title = ""
        except Exception:
            pass

    @rumps.clicked("最近事件")
    def show_events(self, _):
        if self._event_texts:
            msg = "\n".join(self._event_texts[:5])
        else:
            msg = "(暂无事件)"
        rumps.alert("小铃铛 - 最近事件", msg)

    def toggle_push(self, sender):
        self._push_enabled = not self._push_enabled
        sender.title = "恢复推送" if not self._push_enabled else "暂停推送"
        self.status_item.title = (
            "状态: 已暂停" if not self._push_enabled else "状态: 监听中..."
        )

    @property
    def push_enabled(self):
        return self._push_enabled
