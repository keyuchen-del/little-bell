import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from collections import deque

logger = logging.getLogger("little-bell")

app = Flask(__name__)

event_history = deque(maxlen=50)
notifier = None
ui_callback = None


def init_server(bark_notifier, on_event_callback=None):
    global notifier, ui_callback
    notifier = bark_notifier
    ui_callback = on_event_callback


@app.route("/event", methods=["POST"])
def receive_event():
    try:
        payload = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "invalid json"}), 400

    agent = payload.get("agent", "unknown")
    event_type = payload.get("event", "unknown")
    data = payload.get("data", {})
    session_id = data.get("session_id") if isinstance(data, dict) else None

    detail = None
    if isinstance(data, dict):
        detail = data.get("message") or data.get("notification") or data.get("detail")

    event_record = {
        "agent": agent,
        "event": event_type,
        "detail": detail,
        "session_id": session_id,
        "timestamp": datetime.now().isoformat(),
    }
    event_history.appendleft(event_record)

    logger.info(f"[{agent}] {event_type}: {detail or '(no detail)'}")

    if notifier:
        notifier.send_async(event_type, detail=detail, session_id=session_id)

    if ui_callback:
        ui_callback(event_record)

    return jsonify({"ok": True})


@app.route("/status", methods=["GET"])
def status():
    return jsonify({
        "running": True,
        "events_count": len(event_history),
        "recent_events": list(event_history)[:10],
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


def check_port(host, port):
    """Check if port is available. Returns True if free."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False


def run_server(host="127.0.0.1", port=6789):
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    if not check_port(host, port):
        logger.error(
            f"端口 {port} 已被占用! 可能原因:\n"
            f"  1. 小铃铛已在运行 (用 lsof -ti:{port} | xargs kill 关闭)\n"
            f"  2. 其他程序占用了该端口 (用 --port 指定其他端口)"
        )
        return
    app.run(host=host, port=port, threaded=True)
