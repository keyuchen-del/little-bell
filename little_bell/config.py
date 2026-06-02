import os
import yaml
from pathlib import Path

DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


def load_config(path=None):
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    if not config_path.exists():
        return get_defaults()
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_defaults():
    return {
        "bark": {"server": "https://api.day.app", "device_key": ""},
        "notification": {
            "debounce_seconds": 3,
            "notify_on_stop": True,
            "notify_on_notification": True,
            "quiet_start": "",
            "quiet_end": "",
        },
        "pet": {"enabled": True, "position_x": 100, "position_y": 100, "size": 80},
        "server": {"host": "127.0.0.1", "port": 6789},
        "agents": {"claude_code": {"enabled": True, "events": ["Stop", "Notification"]}},
    }


def save_config(config, path=None):
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
