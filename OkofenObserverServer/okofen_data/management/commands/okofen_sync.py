import os
from django.core.management.base import BaseCommand
from django.conf import settings

from src.okofen import read_OkofenConfig, Okofen
from okofen_data.update_db import update_db


class Command(BaseCommand):
    help = "Télécharge les emails Okofen (Gmail) puis importe les CSV dans la base Django."

    def add_arguments(self, parser):
        parser.add_argument(
            "--config",
            dest="config",
            default=os.path.abspath(os.path.join(settings.BASE_DIR, "..", "config_okofen.json")),
            help="Chemin vers le fichier config_okofen.json (défaut: ../config_okofen.json)",
        )
        parser.add_argument(
            "--no-download",
            action="store_true",
            dest="no_download",
            help="N'exécute pas le téléchargement Gmail; importe seulement les CSV locaux.",
        )
        parser.add_argument(
            "--verbose",
            type=int,
            dest="verbose",
            default=1,
            help="Niveau de verbosité (0 silencieux, 1 verbeux)",
        )

    def handle(self, *args, **options):
        config_path = options["config"]
        verbose = int(options["verbose"]) if options["verbose"] is not None else 1
        do_download = not options["no_download"]

        if not os.path.isfile(config_path):
            self.stderr.write(self.style.ERROR(f"Fichier de configuration introuvable: {config_path}"))
            return

        self.stdout.write(f"Config: {config_path}")

        if do_download:
            self.stdout.write("[1/2] Téléchargement des CSV depuis Gmail…")
            try:
                cfg = read_OkofenConfig(config_path)
                okofen = Okofen(cfg, verbose=verbose)
                okofen.download_data_from_gmail()
                self.stdout.write(self.style.SUCCESS("Téléchargement terminé."))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Erreur pendant le téléchargement Gmail: {e}"))
                raise
        else:
            self.stdout.write("Étape Gmail ignorée (--no-download).")

        self.stdout.write("[2/2] Import des CSV locaux vers la base Django…")
        try:
            update_db(verbose=verbose, config_path=config_path)
            self.stdout.write(self.style.SUCCESS("Import terminé."))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Erreur pendant l'import DB: {e}"))
            raise
