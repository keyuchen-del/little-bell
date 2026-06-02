import shutil
import yaml
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.yaml"
EXAMPLE_CONFIG_PATH = PROJECT_ROOT / "config.example.yaml"


def load_config(path=None):
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH

    if not config_path.exists():
        # Auto-copy from example if available
        if EXAMPLE_CONFIG_PATH.exists():
            shutil.copy2(EXAMPLE_CONFIG_PATH, config_path)
        else:
            return get_defaults()

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or get_defaults()


def get_defaults():
    return {
        "macos_notification": {"enabled": True},
        "bark": {"server": "https://api.day.app", "device_key": ""},
        "webhook": {"url": "", "method": "POST", "headers": {"Content-Type": "application/json"}, "body_template": ""},
        "notification": {
            "debounce_seconds": 3,
            "notify_on_stop": True,
            "notify_on_notification": True,
        },
        "pet": {"enabled": True, "position_x": 100, "position_y": 100, "size": 80},
        "server": {"host": "127.0.0.1", "port": 6789},
        "agents": {"claude_code": {"enabled": True, "events": ["Stop", "Notification"]}},
    }


def save_config(config, path=None):
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
