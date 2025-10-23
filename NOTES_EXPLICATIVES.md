# OkofenObserver — Notes explicatives

Ces notes synthétisent le fonctionnement du dépôt et proposent une commande Django pour orchestrer le pipeline données.

## Vue d’ensemble
- Deux flux de données coexistent:
  - `src/okofen.py`: récupère les CSV via Gmail (pièces jointes), maintient une base locale HDF5 et met en forme les données avec pandas.
  - `OkofenObserverServer/okofen_data/update_db.py`: importe les CSV locaux dans la base Django (`RawData`).
- Le serveur Django expose des vues minimales pour interroger les données, et l’admin pour visualiser `RawData`.

## Détail — Récupération et préparation (src/okofen.py)
- `read_OkofenConfig(config_okofen.json)`: lit la config (répertoire des données, compte Gmail, mot de passe applicatif, clé de filtrage, boîte imap).
- `Okofen.download_data_from_gmail()`:
  - Connexion IMAP (via `src/mailler.py`).
  - Recherche des mails par champ IMAP (le code utilise `FROM` avec la clé `email_subject_key_serach` — si la clé est un identifiant de chaudière présent dans le sujet, envisager `SUBJECT`).
  - Télécharge les pièces jointes `touch_*.csv` non présentes dans `data_dir`.
- `Okofen.update_local_db()`:
  - Concatène les nouveaux CSV dans un HDF5 local `0-okofen_db-vendome.h5`.
  - Note: première création — corriger `data = pd.DataFrame()` en `self.data = pd.DataFrame()` si besoin.
- `Okofen.data_format()`: construit une colonne `datetime`, trie et renomme les colonnes (labels FR), convertit en float, indexe par `datetime`.
- `Okofen.Update_db_from_gmail()`: enchaîne téléchargement Gmail → HDF5 → formattage → liste des jours.

## Détail — Import Django (okofen_data)
- Modèle `okofen_data/models.py::RawData`: snapshot de multiples mesures à un `datetime` (unique).
- API `okofen_data/data_api.py`:
  - `get_data_by_dates`, `get_data_for_one_day`, `get_data_for_n_last_days`, journée pivot à 03:00.
- Vues `okofen_data/views.py`:
  - `index`: texte simple.
  - `daygraph`: renvoie (texte) le DataFrame d’un jour (03:00 → +24h).
- `okofen_data/update_db.py::update_db(...)`:
  - Importe incrémentalement les CSV locaux vers `RawData` en ne traitant que les fichiers de date > `Max(datetime)` présent en DB.
  - Renomme les colonnes via un dictionnaire pour correspondre au modèle.

## Commande Django — Pipeline Gmail → DB
Une commande a été ajoutée: `okofen_sync`.

- Emplacement: `okofen_data/management/commands/okofen_sync.py`
- Usage:
  - `cd OkofenObserverServer`
  - `python manage.py okofen_sync` — télécharge les CSV via Gmail puis importe les CSV locaux vers la base Django.
- Options:
  - `--config /chemin/vers/config_okofen.json` (défaut: `../config_okofen.json`)
  - `--no-download` pour ignorer Gmail et importer seulement les CSV déjà présents.
  - `--verbose 0|1` (défaut: 1)
  - `--batch-size N` (défaut: 1000) — insertion en base par lots (bulk_create)

Sous le capot:
- Lit la config, instancie `Okofen`, lance `download_data_from_gmail()` (sauf `--no-download`).
- Enchaîne sur `okofen_data.update_db.update_db(verbose, config_path, batch_size)` pour l’import vers `RawData` (insertion par lots).

## Endpoints Django
- `GET /data/` → texte de diagnostic.
- `GET /data/daydata/<year>/<month>/<day>/graph/` → sérialisation textuelle du DataFrame sur la journée (03:00 → +24h).
- `GET /admin/` → interface d’admin (modèle `RawData`).

### API JSON
- `GET /data/daydata/<year>/<month>/<day>/json/`
  - Retour: `{ "count": <int>, "data": [ { "datetime": ISO8601, ... } ] }`
- `GET /data/range/<YYYY-MM-DD>/<YYYY-MM-DD>/json/`
  - Plage inclusive par jour, avec fenêtres 03:00 → +24h.
  - Retour: `{ "count": <int>, "start": "YYYY-MM-DD", "end": "YYYY-MM-DD", "data": [...] }`
- `GET /data/lastdays/<days>/json/`
  - N derniers jours complets (03:00 → +24h).
  - Retour: `{ "count": <int>, "days": <int>, "data": [...] }`

Remarques:
- `datetime` est sérialisé en chaîne ISO 8601 (timezone-aware).
- Les clés de mesures correspondent aux libellés du modèle (ex: `"T°C Chaudière"`, `"Niveau Sillo kg"`).

## Code possiblement non-utilisé
- `src/plot.py`: utilisé dans le notebook `Okofen_watcher.ipynb`, pas dans le serveur.
- `okofen_data/update_db.py`: module invocable en shell ou via la commande ajoutée; non exposé via vue.
- `tests/OkofenObserver.toml`: méta pour packaging, pas un test automatisé.

## Améliorations suggérées
- IMAP: valider le champ de recherche (`FROM` vs `SUBJECT`).
- Robustesse: corriger l’initialisation `self.data` lors de la première exécution HDF5.
- API: exposer des endpoints JSON (ou DRF) pour les plages de dates et un rendu graphique HTML.
- Unification: la nouvelle commande `okofen_sync` couvre l’orchestration, à automatiser (cron/systemd) si besoin.

***
Dernière mise à jour: ajout de la commande `okofen_sync` et extension de `update_db(verbose=0, config_path=...)` pour choisir le fichier de configuration.
