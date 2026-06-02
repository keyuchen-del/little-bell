"""小铃铛推送模块 — 多通道通知架构。

通道优先级:
1. macOS 系统通知 (零配置，默认开启)
2. Bark (iOS 推送)
3. Webhook (通用 HTTP，覆盖飞书/钉钉/Slack/Discord)
"""
import time
import threading
import subprocess
import logging
from abc import ABC, abstractmethod
from urllib.parse import quote

import requests

logger = logging.getLogger("little-bell")

EVENT_MESSAGES = {
    "stop": {"title": "Agent 等你继续", "body": "任务完成，等待下一步指令"},
    "notification": {"title": "Agent 通知", "body": ""},
    "permission_request": {"title": "需要你批准操作!", "body": "Agent 请求权限确认"},
}


class BaseNotifier(ABC):
    """通知通道基类。"""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def enabled(self) -> bool: ...

    @abstractmethod
    def send(self, title: str, body: str) -> bool: ...


class MacOSNotifier(BaseNotifier):
    """macOS 原生通知 — 零配置，开箱即用。"""

    def __init__(self, config):
        self._enabled = config.get("macos_notification", {}).get("enabled", True)

    @property
    def name(self):
        return "macOS"

    @property
    def enabled(self):
        return self._enabled

    def send(self, title: str, body: str) -> bool:
        script = f'display notification "{body}" with title "{title}" sound name "Glass"'
        try:
            subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, timeout=5,
            )
            return True
        except Exception:
            return False


class BarkNotifier(BaseNotifier):
    """Bark iOS 推送。"""

    def __init__(self, config):
        bark_conf = config.get("bark", {})
        self._server = bark_conf.get("server", "https://api.day.app").rstrip("/")
        self._device_key = bark_conf.get("device_key", "")

    @property
    def name(self):
        return "Bark"

    @property
    def enabled(self):
        return bool(self._device_key)

    def send(self, title: str, body: str) -> bool:
        url = f"{self._server}/{self._device_key}/{quote(title)}/{quote(body)}"
        params = {"sound": "bell", "group": "little-bell"}
        try:
            resp = requests.get(url, params=params, timeout=5)
            return resp.status_code == 200
        except requests.RequestException:
            return False


class WebhookNotifier(BaseNotifier):
    """通用 Webhook — 覆盖飞书/钉钉/Slack/Discord/企业微信等。"""

    def __init__(self, config):
        wh_conf = config.get("webhook", {})
        self._url = wh_conf.get("url", "")
        self._method = wh_conf.get("method", "POST").upper()
        self._headers = wh_conf.get("headers", {"Content-Type": "application/json"})
        self._body_template = wh_conf.get("body_template", "")

    @property
    def name(self):
        return "Webhook"

    @property
    def enabled(self):
        return bool(self._url)

    def send(self, title: str, body: str) -> bool:
        if self._body_template:
            payload = self._body_template.replace("{{title}}", title).replace("{{body}}", body)
        else:
            import json
            payload = json.dumps({"title": title, "body": body, "source": "little-bell"})

        try:
            resp = requests.request(
                self._method, self._url,
                data=payload.encode("utf-8"),
                headers=self._headers,
                timeout=10,
            )
            return 200 <= resp.status_code < 300
        except requests.RequestException:
            return False


class NotifierManager:
    """多通道通知管理器 — 防抖 + 依次推送所有已启用通道。"""

    def __init__(self, config):
        self._notifiers: list[BaseNotifier] = [
            MacOSNotifier(config),
            BarkNotifier(config),
            WebhookNotifier(config),
        ]
        self._debounce_seconds = config.get("notification", {}).get("debounce_seconds", 3)
        self._notify_on_stop = config.get("notification", {}).get("notify_on_stop", True)
        self._notify_on_notification = config.get("notification", {}).get("notify_on_notification", True)
        self._last_push_time: dict[str, float] = {}
        self._lock = threading.Lock()

    @property
    def active_channels(self) -> list[str]:
        return [n.name for n in self._notifiers if n.enabled]

    def should_notify(self, event_type: str, session_id: str = None) -> bool:
        if event_type == "stop" and not self._notify_on_stop:
            return False
        if event_type == "notification" and not self._notify_on_notification:
            return False

        with self._lock:
            key = f"{session_id or 'default'}:{event_type}"
            now = time.time()
            if now - self._last_push_time.get(key, 0) < self._debounce_seconds:
                return False
            self._last_push_time[key] = now
        return True

    def send(self, event_type: str, detail: str = None, session_id: str = None) -> bool:
        if not self.should_notify(event_type, session_id):
            return False

        msg = EVENT_MESSAGES.get(event_type, {"title": "小铃铛", "body": event_type})
        title = msg["title"]
        body = detail if detail else msg["body"]

        any_success = False
        for notifier in self._notifiers:
            if notifier.enabled:
                try:
                    ok = notifier.send(title, body)
                    if ok:
                        any_success = True
                        logger.debug(f"[{notifier.name}] push OK")
                except Exception as e:
                    logger.warning(f"[{notifier.name}] push failed: {e}")
        return any_success

    def send_async(self, event_type: str, detail: str = None, session_id: str = None):
        t = threading.Thread(
            target=self.send,
            args=(event_type, detail, session_id),
            daemon=True,
        )
        t.start()
