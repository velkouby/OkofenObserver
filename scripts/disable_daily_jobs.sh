#!/usr/bin/env bash
set -euo pipefail

# Removes daily cron jobs for okofen_sync and compute_dailystats.

MARKER_PATTERN='OKOFEN_OBSERVER_'

current_cron="$(crontab -l 2>/dev/null || true)"

if [[ -z "$current_cron" ]]; then
  echo "No crontab entries found for current user." >&2
  exit 0
fi

filtered_cron="$(printf '%s\n' "$current_cron" | grep -v "$MARKER_PATTERN" || true)"

if [[ "$filtered_cron" == "$current_cron" ]]; then
  echo "No OkofenObserver cron entries to remove." >&2
  exit 0
fi

if [[ -z "${filtered_cron//[[:space:]]/}" ]]; then
  crontab -r
else
  printf '%s\n' "$filtered_cron" | crontab -
fi

echo "Removed OkofenObserver daily cron jobs." >&2
