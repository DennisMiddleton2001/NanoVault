#!/usr/bin/env bash
TARGET_DIR="/home/darth-tedious/.sovereign-ai/ComfyUI/custom_nodes"

echo "=== ComfyUI Custom Node Audit ==="
echo "Scanning directory: $TARGET_DIR"
echo "--------------------------------------------------------"

# 1. Flag privilege escalation (sudo / pkexec)
echo "[!] Checking for sudo / root elevation calls..."
grep -rnE "(sudo|pkexec)\s+" "$TARGET_DIR" \
  --exclude-dir=".git" --exclude="*.log" --exclude="*.md" 2>/dev/null || echo "    Clean: No raw sudo calls detected."

echo "--------------------------------------------------------"

# 2. Flag network requests, socket connections, and downloads
echo "[!] Checking for outbound network/download calls..."
grep -rnE "(requests\.(get|post|put|delete)|urllib\.request|aiohttp\.ClientSession|httpx\.(get|post)|socket\.socket|git clone|wget|curl)" "$TARGET_DIR" \
  --exclude-dir=".git" --exclude="*.log" --exclude="*.md" 2>/dev/null || echo "    Clean: No direct outbound network calls detected."

echo "--------------------------------------------------------"

# 3. Flag analytics, telemetry, and metrics reporting
echo "[!] Checking for telemetry / tracking keywords..."
grep -rnEi "(telemetry|analytics|mixpanel|posthog|segment\.io|sentry_sdk|datadog)" "$TARGET_DIR" \
  --exclude-dir=".git" --exclude="*.log" --exclude="*.md" 2>/dev/null || echo "    Clean: No common telemetry trackers detected."

echo "--------------------------------------------------------"

# 4. Flag shell subprocess calls
echo "[!] Checking for shell subprocess / system execution..."
grep -rnE "(subprocess\.(Popen|run|call|check_output)|os\.system|os\.popen)" "$TARGET_DIR" \
  --exclude-dir=".git" --exclude="*.log" --exclude="*.md" 2>/dev/null || echo "    Clean: No shell executions detected."

echo "--------------------------------------------------------"
echo "Audit complete."
