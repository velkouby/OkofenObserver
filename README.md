# OkfenObserver
System to get data from your Okofen by email


python -m venv venv_okofen
source ./venv_okofen/bin/activate
pip install --upgrade pip
pip install -r ./requirements.txt



'''
Create your own config_okofen.json file with your Gmail application credentials and the filter with your Okfen boiler ID name
{
    "data_dir":"~/dev/data/okfen",
    "gmail_acount":"your.email@gmail.com",
    "gmail_passwd":"[Gmail application pass]",
    "email_subject_key_serach":"P0060C6_42F21A",
    "gmail_box":"INBOX"    
}

'''

# Create Gmail app passworld

https://support.google.com/mail/answer/185833?hl=en


# Run server
python manage.py runserver
python manage.py shell

## Sync command (Gmail → CSV → DB)

From `OkofenObserverServer/`, run:

```
python manage.py okofen_sync [--config ../config_okofen.json] [--no-download] [--verbose 1] [--batch-size 1000]
```

Options:
- `--config` path to `config_okofen.json` (default: `../config_okofen.json`)
- `--no-download` skip Gmail; import only existing local CSV files
- `--verbose 0|1` logging level
- `--batch-size N` database insert batch size (default 1000)

## Daily statistics

The Django app precomputes daily aggregates in the `DailyStat` table. After importing new data you can tidy up or backfill with:

```
python manage.py compute_dailystats --days 30      # create stats for the last 30 days (missing only)
python manage.py compute_dailystats --from 2025-02-01 --to 2025-02-07
python manage.py compute_dailystats --force --from 2025-02-01 --to 2025-02-07
python manage.py compute_dailystats --all          # clean duplicates + recompute everything
```

Flags:
- `--days N` (default 30) builds stats for the previous N days if missing.
- `--from YYYY-MM-DD` (optional `--to YYYY-MM-DD`) targets an explicit range.
- `--force` recomputes even if a `DailyStat` already exists for a day.
- `--all` cleans duplicate rows then recomputes every available day (ignores other options).

## Automation

You can automate `okofen_sync` and `compute_dailystats` once per day with cron or systemd.

### Cron helper scripts

- Run `bash scripts/enable_daily_jobs.sh` to install two cron entries for the current user:
  - `okofen_sync` at 03:00.
  - `compute_dailystats --days 30` at 03:30.
- Override the times by exporting `SYNC_TIME=HH:MM` and/or `STATS_TIME=HH:MM` before running the script.
- Logs are written under `cron_logs/` in the project root (`okofen_sync.log`, `compute_dailystats.log`).
- Remove the jobs with `bash scripts/disable_daily_jobs.sh`.

### Manual crontab

If you prefer to edit the crontab yourself, add entries similar to:

```
0 3 * * * cd ~/dev/OkofenObserver/OkofenObserverServer && ~/dev/OkofenObserver/venv_okofen/bin/python manage.py okofen_sync --config ~/dev/OkofenObserver/config_okofen.json >> ~/okofen_sync.log 2>&1
30 3 * * * cd ~/dev/OkofenObserver/OkofenObserverServer && ~/dev/OkofenObserver/venv_okofen/bin/python manage.py compute_dailystats --days 30 >> ~/okofen_stats.log 2>&1
```

Ensure the paths match your local installation.

### Systemd timers

For long-running servers, you can create two user-level systemd units:

- `~/.config/systemd/user/okofen_sync.service` / `.timer` with `OnCalendar=*-*-* 03:00:00` running `python manage.py okofen_sync`.
- `~/.config/systemd/user/compute_dailystats.service` / `.timer` with `OnCalendar=*-*-* 03:30:00` running `python manage.py compute_dailystats --days 30`.

Enable timers with `systemctl --user enable --now okofen_sync.timer compute_dailystats.timer`.

## JSON API

The Django app exposes minimal JSON endpoints under `/data/` (day window starts at 03:00):

- `GET /data/daydata/<year>/<month>/<day>/json/`
  - Returns: `{ "count": <int>, "data": [ { "datetime": ISO8601, ... } ] }`

- `GET /data/range/<YYYY-MM-DD>/<YYYY-MM-DD>/json/`
  - Inclusive day range, using 03:00 boundaries.
  - Returns: `{ "count": <int>, "start": "YYYY-MM-DD", "end": "YYYY-MM-DD", "data": [...] }`

- `GET /data/lastdays/<days>/json/`
  - Last N whole days (03:00 → +24h).
  - Returns: `{ "count": <int>, "days": <int>, "data": [...] }`

Notes:
- Timestamps are timezone-aware (ISO 8601 strings).
- Values correspond to model fields (French labels), e.g. `"T°C Chaudière"`, `"Niveau Sillo kg"`, etc.
