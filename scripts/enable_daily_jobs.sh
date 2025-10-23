#!/usr/bin/env bash
set -euo pipefail

# Adds daily cron jobs for okofen_sync and compute_dailystats.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SERVER_DIR="$PROJECT_ROOT/OkofenObserverServer"
PYTHON_BIN="$PROJECT_ROOT/venv_okofen/bin/python"
CONFIG_PATH="$PROJECT_ROOT/config_okofen.json"
LOG_DIR="$PROJECT_ROOT/cron_logs"

SYNC_TIME="${SYNC_TIME:-03:00}"
STATS_TIME="${STATS_TIME:-03:30}"

validate_time() {
  local value="$1"
  if [[ ! "$value" =~ ^([01][0-9]|2[0-3]):([0-5][0-9])$ ]]; then
    echo "Invalid time format: $value (expected HH:MM)" >&2
    exit 1
  fi
}

validate_time "$SYNC_TIME"
validate_time "$STATS_TIME"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Missing virtualenv Python at $PYTHON_BIN" >&2
  exit 1
fi

if [[ ! -f "$CONFIG_PATH" ]]; then
  echo "Missing configuration file at $CONFIG_PATH" >&2
  exit 1
fi

mkdir -p "$LOG_DIR"

sync_hour="${SYNC_TIME%:*}"
sync_minute="${SYNC_TIME#*:}"
stats_hour="${STATS_TIME%:*}"
stats_minute="${STATS_TIME#*:}"

sync_log="$LOG_DIR/okofen_sync.log"
stats_log="$LOG_DIR/compute_dailystats.log"

sync_command="$sync_minute $sync_hour * * * cd \"$SERVER_DIR\" && \"$PYTHON_BIN\" manage.py okofen_sync --config \"$CONFIG_PATH\" >> \"$sync_log\" 2>&1 # OKOFEN_OBSERVER_SYNC"
stats_command="$stats_minute $stats_hour * * * cd \"$SERVER_DIR\" && \"$PYTHON_BIN\" manage.py compute_dailystats --days 30 >> \"$stats_log\" 2>&1 # OKOFEN_OBSERVER_DAILYSTATS"

existing_cron="$(crontab -l 2>/dev/null || true)"

filtered_cron="$(printf '%s\n' "$existing_cron" | grep -v 'OKOFEN_OBSERVER_' || true)"

tmpfile="$(mktemp)"

if [[ -n "$filtered_cron" ]]; then
  printf '%s\n' "$filtered_cron" > "$tmpfile"
fi

printf '%s\n' "$sync_command" >> "$tmpfile"
printf '%s\n' "$stats_command" >> "$tmpfile"

crontab "$tmpfile"
rm -f "$tmpfile"

echo "Installed daily cron jobs:" >&2
echo "- okofen_sync at $SYNC_TIME" >&2
echo "- compute_dailystats at $STATS_TIME" >&2
