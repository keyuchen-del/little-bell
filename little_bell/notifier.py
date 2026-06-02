import time
import threading
import requests
from urllib.parse import quote

EVENT_MESSAGES = {
    "stop": {"title": "Claude Code 等你继续", "body": "任务完成，等待下一步指令~"},
    "notification": {"title": "Claude Code 通知", "body": ""},
    "permission_request": {"title": "需要你批准操作!", "body": "Claude Code 请求权限确认"},
}


class BarkNotifier:
    def __init__(self, config):
        self.server = config["bark"]["server"].rstrip("/")
        self.device_key = config["bark"]["device_key"]
        self.debounce_seconds = config["notification"]["debounce_seconds"]
        self.notify_on_stop = config["notification"]["notify_on_stop"]
        self.notify_on_notification = config["notification"]["notify_on_notification"]
        self._last_push_time = {}
        self._lock = threading.Lock()

    @property
    def is_configured(self):
        return bool(self.device_key)

    def should_notify(self, event_type, session_id=None):
        if not self.is_configured:
            return False
        if event_type == "stop" and not self.notify_on_stop:
            return False
        if event_type == "notification" and not self.notify_on_notification:
            return False

        with self._lock:
            key = f"{session_id or 'default'}:{event_type}"
            now = time.time()
            last = self._last_push_time.get(key, 0)
            if now - last < self.debounce_seconds:
                return False
            self._last_push_time[key] = now
        return True

    def send(self, event_type, detail=None, session_id=None):
        if not self.should_notify(event_type, session_id):
            return False

        msg = EVENT_MESSAGES.get(event_type, {"title": "小铃铛", "body": event_type})
        title = msg["title"]
        body = detail if detail else msg["body"]

        url = f"{self.server}/{self.device_key}/{quote(title)}/{quote(body)}"
        params = {"sound": "bell", "group": "little-bell", "icon": ""}

        try:
            resp = requests.get(url, params=params, timeout=5)
            return resp.status_code == 200
        except requests.RequestException:
            return False

    def send_async(self, event_type, detail=None, session_id=None):
        t = threading.Thread(
            target=self.send,
            args=(event_type, detail, session_id),
            daemon=True,
        )
        t.start()
