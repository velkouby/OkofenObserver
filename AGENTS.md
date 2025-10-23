# Repository Guidelines

## Project Structure & Module Organization
- `OkofenObserverServer/` hosts the Django project, custom management commands, and static assets; run all Django tools from this folder.
- `src/` contains standalone data utilities (`okofen.py`, `mailler.py`) that push raw CSVs into the Django pipeline.
- `scripts/` provides cron helpers and maintenance workflows; treat them as the single source of truth for scheduled jobs.
- `data/` and `config_okofen.json` are developer-local; do not commit credentials or generated CSV exports.

## Build, Test, and Development Commands
- `python -m venv venv_okofen && source venv_okofen/bin/activate` creates an isolated environment for tooling and the Django app.
- `pip install -r requirements.txt` installs both the Django runtime and data-processing dependencies.
- `cd OkofenObserverServer && python manage.py runserver` launches the local dashboard under the default Django port.
- `python manage.py okofen_sync --config ../config_okofen.json [--no-download]` ingests Gmail exports into CSV and the database.
- `python manage.py compute_dailystats --days 30` refreshes cached aggregates after new imports; pair large recomputations with `--force` or `--all` when needed.
- `bash scripts/enable_daily_jobs.sh` installs cron entries; use `disable_daily_jobs.sh` to remove them.

## Coding Style & Naming Conventions
- Follow PEP 8 with 4-space indentation, descriptive snake_case function names, and PascalCase for Django models and classes.
- Group Django views, serializers, and management commands by feature directory; prefer module-level constants over magic numbers in both `src/` and Django apps.
- Use type hints for new functions, and keep docstrings focused on side effects and expected inputs.
- Run `python -m compileall src OkofenObserverServer` or your editor’s linting prior to pushing when possible.

## Testing Guidelines
- Execute `cd OkofenObserverServer && python manage.py test` before submitting; add targeted tests alongside each app’s `tests.py` or under `tests/` for integration utilities.
- Name test cases after the behavior under examination (e.g., `test_compute_dailystats_skips_existing_day`).
- Provide fixture JSON or CSV files inside `OkofenObserverServer/okofen_data/fixtures/` and clean them up when they are temporary.

## Commit & Pull Request Guidelines
- Use imperative, scope-rich commit messages (e.g., `Add daily statistics management command`) and keep summaries under ~72 characters.
- Reference related issues in the body and describe data sources touched (Gmail, CSV, cron) to aid reviewers.
- Include a checklist in PR descriptions: setup steps, commands executed, screenshots for UI changes, and verification of cron scripts if modified.

## Security & Configuration Tips
- Never commit `config_okofen.json` values; store Gmail credentials in local `.env` files or secret managers instead.
- Rotate Gmail app passwords when onboarding contributors, and document local paths for `data_dir` in PR notes.
- When sharing logs, strip boiler identifiers and user emails before attaching them to reviews.
