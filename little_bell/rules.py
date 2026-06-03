"""规则引擎 — 自动批准/拒绝匹配的操作，减少手动干预。

config.yaml 中配置:
  rules:
    auto_allow:
      - "Read"                    # 所有 Read 操作自动批准
      - "Bash:ls *"              # ls 开头的命令自动批准
      - "Bash:git status"        # git status 自动批准
      - "Bash:git diff*"         # git diff 相关自动批准
      - "Edit:*.md"              # 编辑 markdown 自动批准
    auto_deny:
      - "Bash:rm -rf *"          # rm -rf 永远拒绝
      - "Bash:sudo *"            # sudo 永远拒绝
    ask:
      - "*"                      # 其他都问用户 (默认行为)
"""
import fnmatch
import logging

logger = logging.getLogger("little-bell")


class RuleEngine:
    def __init__(self, config):
        rules_conf = config.get("rules", {})
        self._auto_allow = rules_conf.get("auto_allow", [])
        self._auto_deny = rules_conf.get("auto_deny", [])

    def evaluate(self, tool_name: str, tool_input: dict) -> str | None:
        """评估规则。返回 'allow' / 'deny' / None (需要人工决定)。"""
        pattern_key = self._make_pattern_key(tool_name, tool_input)

        for pattern in self._auto_deny:
            if self._match(pattern, tool_name, pattern_key):
                logger.info(f"[Rules] auto_deny: {pattern} matched {pattern_key[:60]}")
                return "deny"

        for pattern in self._auto_allow:
            if self._match(pattern, tool_name, pattern_key):
                logger.info(f"[Rules] auto_allow: {pattern} matched {pattern_key[:60]}")
                return "allow"

        return None

    def _make_pattern_key(self, tool_name: str, tool_input: dict) -> str:
        """构建用于匹配的 key，格式: Tool:content"""
        if not isinstance(tool_input, dict):
            return f"{tool_name}:{tool_input}"

        if tool_name == "Bash":
            return f"Bash:{tool_input.get('command', '')}"
        elif tool_name == "Edit":
            return f"Edit:{tool_input.get('file_path', '')}"
        elif tool_name == "Write":
            return f"Write:{tool_input.get('file_path', '')}"
        elif tool_name == "Read":
            return f"Read:{tool_input.get('file_path', '')}"
        else:
            return f"{tool_name}:"

    def _match(self, pattern: str, tool_name: str, pattern_key: str) -> bool:
        """模式匹配。支持:
        - "Read" — 匹配所有 Read 操作
        - "Bash:git *" — 匹配 Bash 中 git 开头的命令
        - "*" — 匹配所有
        """
        if pattern == "*":
            return True

        if ":" not in pattern:
            return tool_name == pattern

        return fnmatch.fnmatch(pattern_key, pattern)
