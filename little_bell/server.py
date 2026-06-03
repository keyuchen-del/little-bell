import json
import uuid
import socket
import logging
import threading
from datetime import datetime
from flask import Flask, request, jsonify, Response
from collections import deque

logger = logging.getLogger("little-bell")

app = Flask(__name__)

event_history = deque(maxlen=50)
notifier = None
ui_callback = None

# Pending permission actions: {action_id: {event, tool, params, decision, decided_event}}
pending_actions = {}
pending_lock = threading.Lock()


def get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


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


# ============================================================
# Permission Request — 手机远程批准/拒绝
# ============================================================

@app.route("/permission", methods=["POST"])
def handle_permission():
    """Claude Code PermissionRequest HTTP hook 端点。
    阻塞直到用户在手机上做出决定，或超时。
    """
    try:
        payload = request.get_json(force=True) or {}
    except Exception:
        payload = {}

    tool_name = payload.get("tool", payload.get("toolName", "unknown"))
    tool_input = payload.get("input", payload.get("toolInput", {}))
    session_id = payload.get("session_id", "")

    # Summarize what's being requested
    if isinstance(tool_input, dict):
        summary = tool_input.get("command", "") or tool_input.get("file_path", "") or json.dumps(tool_input, ensure_ascii=False)[:200]
    else:
        summary = str(tool_input)[:200]

    action_id = uuid.uuid4().hex[:12]
    decided_event = threading.Event()

    action = {
        "id": action_id,
        "tool": tool_name,
        "summary": summary,
        "full_input": tool_input,
        "session_id": session_id,
        "decision": None,
        "decided_event": decided_event,
        "timestamp": datetime.now().isoformat(),
    }

    with pending_lock:
        pending_actions[action_id] = action

    logger.info(f"[Permission] {tool_name}: {summary[:60]}... (waiting for decision)")

    # Push notification with action URL
    lan_ip = get_lan_ip()
    port = request.host.split(":")[-1] if ":" in request.host else "6789"
    action_url = f"http://{lan_ip}:{port}/action/{action_id}"

    if notifier:
        notifier.send_permission(
            tool_name=tool_name,
            summary=summary,
            action_url=action_url,
            session_id=session_id,
        )

    if ui_callback:
        ui_callback({
            "agent": "claude-code",
            "event": "permission_request",
            "detail": f"[等待批准] {tool_name}: {summary[:50]}",
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
        })

    # Block until user decides or timeout (5 min)
    decided_event.wait(timeout=300)

    decision = action.get("decision", "deny")

    with pending_lock:
        pending_actions.pop(action_id, None)

    logger.info(f"[Permission] {tool_name} → {decision}")

    if decision == "allow":
        return jsonify({"decision": "allow"})
    else:
        return jsonify({"decision": "deny", "reason": "User denied from mobile"})


@app.route("/action/<action_id>", methods=["GET"])
def action_page(action_id):
    """手机端操作页面 — 显示批准/拒绝按钮。"""
    with pending_lock:
        action = pending_actions.get(action_id)

    if not action:
        return Response(ACTION_PAGE_EXPIRED, content_type="text/html; charset=utf-8")

    html = ACTION_PAGE_TEMPLATE.format(
        action_id=action_id,
        tool=action["tool"],
        summary=action["summary"][:300],
        timestamp=action["timestamp"],
    )
    return Response(html, content_type="text/html; charset=utf-8")


@app.route("/action/<action_id>/approve", methods=["POST", "GET"])
def action_approve(action_id):
    return _resolve_action(action_id, "allow")


@app.route("/action/<action_id>/deny", methods=["POST", "GET"])
def action_deny(action_id):
    return _resolve_action(action_id, "deny")


def _resolve_action(action_id, decision):
    with pending_lock:
        action = pending_actions.get(action_id)

    if not action:
        return Response(ACTION_PAGE_DONE.format(result="已过期或已处理"), content_type="text/html; charset=utf-8")

    action["decision"] = decision
    action["decided_event"].set()

    result_text = "✅ 已批准" if decision == "allow" else "❌ 已拒绝"
    return Response(ACTION_PAGE_DONE.format(result=result_text), content_type="text/html; charset=utf-8")


@app.route("/actions", methods=["GET"])
def list_actions():
    """列出所有待处理的 permission 请求。"""
    with pending_lock:
        items = [
            {"id": a["id"], "tool": a["tool"], "summary": a["summary"], "timestamp": a["timestamp"]}
            for a in pending_actions.values()
            if a["decision"] is None
        ]
    return jsonify({"pending": items})


# ============================================================
# Existing endpoints
# ============================================================

@app.route("/status", methods=["GET"])
def status():
    with pending_lock:
        pending_count = sum(1 for a in pending_actions.values() if a["decision"] is None)
    return jsonify({
        "running": True,
        "events_count": len(event_history),
        "pending_actions": pending_count,
        "recent_events": list(event_history)[:10],
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "lan_ip": get_lan_ip()})


def check_port(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False


def run_server(host="0.0.0.0", port=6789):
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    if not check_port(host, port):
        logger.error(
            f"端口 {port} 已被占用! 可能原因:\n"
            f"  1. 小铃铛已在运行 (用 lsof -ti:{port} | xargs kill 关闭)\n"
            f"  2. 其他程序占用了该端口 (用 --port 指定其他端口)"
        )
        return
    app.run(host=host, port=port, threaded=True)


# ============================================================
# HTML Templates (inline, mobile-optimized)
# ============================================================

ACTION_PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, user-scalable=no">
<title>小铃铛 - 权限请求</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #1a1a2e; color: #eee; min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px; }}
.card {{ background: #16213e; border-radius: 20px; padding: 32px 24px; max-width: 400px; width: 100%; box-shadow: 0 20px 60px rgba(0,0,0,0.5); }}
.icon {{ text-align: center; font-size: 48px; margin-bottom: 16px; }}
h1 {{ font-size: 20px; text-align: center; margin-bottom: 8px; color: #fff; }}
.tool {{ background: #0f3460; border-radius: 10px; padding: 12px 16px; margin: 16px 0; font-family: monospace; font-size: 14px; word-break: break-all; color: #a8d8ea; }}
.summary {{ color: #aaa; font-size: 13px; margin-bottom: 24px; word-break: break-all; max-height: 120px; overflow-y: auto; }}
.buttons {{ display: flex; gap: 12px; }}
.btn {{ flex: 1; padding: 16px; border: none; border-radius: 12px; font-size: 18px; font-weight: 600; cursor: pointer; transition: transform 0.1s; }}
.btn:active {{ transform: scale(0.95); }}
.btn-approve {{ background: #00c853; color: #fff; }}
.btn-deny {{ background: #ff1744; color: #fff; }}
.time {{ text-align: center; color: #666; font-size: 11px; margin-top: 16px; }}
</style>
</head>
<body>
<div class="card">
  <div class="icon">🔔</div>
  <h1>Agent 请求权限</h1>
  <div class="tool">{tool}</div>
  <div class="summary">{summary}</div>
  <div class="buttons">
    <button class="btn btn-approve" onclick="decide('approve')">批准</button>
    <button class="btn btn-deny" onclick="decide('deny')">拒绝</button>
  </div>
  <div class="time">{timestamp}</div>
</div>
<script>
function decide(action) {{
  fetch('/action/{action_id}/' + action, {{method: 'POST'}})
    .then(() => {{
      document.querySelector('.card').innerHTML = '<div class="icon">' + (action==='approve' ? '✅' : '❌') + '</div><h1>' + (action==='approve' ? '已批准' : '已拒绝') + '</h1><p style="text-align:center;color:#aaa;margin-top:12px">可以关闭此页面</p>';
    }})
    .catch(() => {{ alert('发送失败，请重试'); }});
}}
</script>
</body>
</html>"""

ACTION_PAGE_EXPIRED = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>小铃铛</title>
<style>
body { font-family: -apple-system, sans-serif; background: #1a1a2e; color: #eee; min-height: 100vh; display: flex; align-items: center; justify-content: center; }
.card { text-align: center; padding: 40px; }
</style>
</head>
<body><div class="card"><p style="font-size:48px">⏰</p><h2>请求已过期或已处理</h2></div></body>
</html>"""

ACTION_PAGE_DONE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>小铃铛</title>
<style>
body {{ font-family: -apple-system, sans-serif; background: #1a1a2e; color: #eee; min-height: 100vh; display: flex; align-items: center; justify-content: center; }}
.card {{ text-align: center; padding: 40px; }}
</style>
</head>
<body><div class="card"><h2>{result}</h2><p style="color:#aaa;margin-top:12px">可以关闭此页面</p></div></body>
</html>"""
