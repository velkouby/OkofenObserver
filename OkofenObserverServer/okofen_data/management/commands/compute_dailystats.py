from datetime import datetime, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone as djtz

from okofen_data import daily_stats


class Command(BaseCommand):
    help = (
        "Calcule et met à jour les agrégats quotidiens (DailyStat) à partir "
        "des données RawData. Par défaut, seules les 30 dernières journées sont "
        "recalculées."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            dest="days",
            default=30,
            help="Nombre de jours récents à recalculer (par défaut 30).",
        )
        parser.add_argument(
            "--from",
            dest="start",
            help="Date de début incluse au format YYYY-MM-DD (prioritaire sur --days).",
        )
        parser.add_argument(
            "--to",
            dest="end",
            help="Date de fin incluse au format YYYY-MM-DD (optionnelle).",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            dest="recompute_all",
            help="Recalcule toutes les journées disponibles (ignore les autres options).",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            dest="force",
            help="Recalcule les journées même si une statistique existe déjà.",
        )

    def handle(self, *args, **options):
        if options.get("recompute_all"):
            self.stdout.write("Recalcul complet de toutes les journées…")
            removed = daily_stats.cleanup_duplicates()
            stats = daily_stats.recompute_all()
            msg = f"{len(stats)} journée(s) recalculée(s)."
            if removed:
                msg += f" {removed} doublon(s) supprimé(s)."
            self.stdout.write(self.style.SUCCESS(msg))
            return

        start_opt = options.get("start")
        end_opt = options.get("end")

        if start_opt:
            try:
                start_dt = datetime.strptime(start_opt, "%Y-%m-%d")
            except ValueError as exc:
                raise CommandError(f"Date de début invalide: {start_opt}") from exc
            start_day = start_dt.date()

            if end_opt:
                try:
                    end_dt = datetime.strptime(end_opt, "%Y-%m-%d")
                except ValueError as exc:
                    raise CommandError(f"Date de fin invalide: {end_opt}") from exc
                end_day = end_dt.date()
            else:
                end_day = start_day

            if end_day < start_day:
                raise CommandError("La date de fin doit être >= date de début.")

            days = [start_day + timedelta(days=i) for i in range((end_day - start_day).days + 1)]
        else:
            days_count = options.get("days", 30)
            if days_count <= 0:
                raise CommandError("--days doit être > 0.")
            today = djtz.localtime(djtz.now()).date()
            days = [today - timedelta(days=i) for i in range(days_count)]

        removed = daily_stats.cleanup_duplicates(days)
        force = options.get("force")
        stats = daily_stats.compute_for_days(days, skip_existing=not force)

        if force:
            action = "recalculée(s)"
        else:
            action = "créée(s)"

        msg = f"{len(stats)} journée(s) {action}."
        if removed:
            msg += f" {removed} doublon(s) supprimé(s)."
        self.stdout.write(self.style.SUCCESS(msg))
