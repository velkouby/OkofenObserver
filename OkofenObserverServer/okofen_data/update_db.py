from src.okofen import *
from okofen_data.models import RawData
from django.db.models import Max
import datetime as dt
from django.utils.timezone import make_aware

dico = {
    'datetime':'datetime',
    'AT [°C]': 'T°C Extérieure',
    'HK1 RT Ist[°C]': 'T°C Ambiante',
    'HK1 RT Soll[°C]': 'T°C Ambiante Consigne',
    'PE1 Fuellstand[kg]' : 'Niveau Sillo kg',
    'PE1 Fuellstand ZWB[kg]' : 'Niveau tremis kg',
    'PE1 KT[°C]': 'T°C Chaudière',
    'PE1 KT_SOLL[°C]': 'T°C Chaudière Consigne',
    'PE1 Modulation[%]':'PE1 Modulation[%]',
    'PE1 FRT Ist[°C]':'T°C Flamme',
    'PE1 FRT Soll[°C]':'T°C Flamme Consigne',
    'HK1 VL Ist[°C]': 'T°C Départ',
    'HK1 VL Soll[°C]': 'T°C Départ Consigne',
    'HK1 Pumpe': 'Circulateur Chauffage (On/Off)',
    'HK1 Status':"Status Chauff.",
    'WW1 EinT Ist[°C]':'T°C ECS',
    'WW1 AusT Ist[°C]':'T°C ECS (arret)',
    'WW1 Soll[°C]':'T°C ECS Consigne',
    'WW1 Pumpe':'Circulateur ECS',
    'WW1 Status':'Status ESC',
}

def get_date_from_filename(filename:str)->dt.date:
    tmp = s.basename(filename).split('_')[1]
    return dt.date(year=int(tmp[:4]), month=int(tmp[4:6]),day=int(tmp[6:8]))

def update_db(verbose=0, config_path: str = "../config_okofen.json", batch_size: int = 1000):
    """
    Importe les fichiers CSV locaux Okofen dans la base Django (modèle RawData).

    - verbose: niveau de log (0 = silencieux)
    - config_path: chemin vers le fichier config_okofen.json
    - batch_size: taille des lots pour l'insertion en base
    """
    config = read_OkofenConfig(config_path)
    okofen = Okofen(config)
    #okofen.download_data_from_gmail()
    agg_max = RawData.objects.aggregate(Max('datetime'))['datetime__max']
    if agg_max is None:
        # Table vide: démarrer à une date très ancienne pour importer tout
        date_max = dt.date(1900, 1, 1)
    else:
        date_max = agg_max.date()
    local_files = okofen.get_local_datafile_list()
    local_files.sort()
    files_by_date={}
    for filename in local_files:
        files_by_date[get_date_from_filename(filename)]=filename

    for current_date in sorted(files_by_date.keys()):
        filename = files_by_date[current_date]
        if verbose>0:
            print(f"read {filename}")
        if current_date>date_max:
            current = read_okfen_data(filename)
            if current is None:
                continue
            if verbose>0:
                print(f"Start to add {current.shape[0]} data")
            # Normaliser fortement les noms de colonnes
            def _norm(c: str) -> str:
                c = str(c).lstrip("\ufeff").strip()
                c = c.replace("\u00a0", " ")  # nbsp -> espace normal
                c = " ".join(c.split())       # compresser espaces multiples
                return c

            current.columns = [_norm(c) for c in current.columns]

            # Supprimer lignes d'entête répliquées: si une ligne contient exactement les libellés de colonnes
            header_set = set(current.columns)
            mask_header_dup = current.apply(lambda r: set(str(x).strip() for x in r.values) == header_set, axis=1)
            if mask_header_dup.any():
                current = current[~mask_header_dup]

            # Dictionnaires d'alias pour colonnes date/heure
            lower_map = {c.lower(): c for c in current.columns}
            date_aliases = [
                "datum", "date", "jour", "datum (date)", "date (local)", "date (utc)",
                "date/ jour", "date jour"
            ]
            time_aliases = [
                "zeit", "time", "heure", "uhrzeit", "heure locale", "heure (local)", "heure (utc)",
                "uhrzeit [hh:mm:ss]"
            ]
            datetime_aliases = [
                "datetime", "timestamp", "date time", "date_time", "date-heure", "dateheure",
                "date/heure", "date-heure", "horodatage", "zeitstempel", "zeitpunkt",
                "timestamp (utc)", "datetime (utc)", "datetime (local)", "date-time"
            ]

            # Trouver colonnes
            dcol = next((lower_map[a] for a in date_aliases if a in lower_map), None)
            tcol = next((lower_map[a] for a in time_aliases if a in lower_map), None)
            dtcol = next((lower_map[a] for a in datetime_aliases if a in lower_map), None)

            # Construire 'datetime'
            import pandas as pd
            if dtcol:
                # Colonne datetime unique
                dt_str = current[dtcol].astype(str).str.strip()
                current["datetime"] = pd.to_datetime(dt_str, errors="coerce", dayfirst=True, infer_datetime_format=True)
            elif dcol and tcol:
                dt_str = (current[dcol].astype(str).str.strip() + " " + current[tcol].astype(str).str.strip()).str.strip()
                dt_str = dt_str.replace({"": pd.NA, "NaN": pd.NA, "None": pd.NA})
                current["datetime"] = pd.to_datetime(dt_str, format="%d.%m.%Y %H:%M:%S", errors="coerce", dayfirst=True)
                if current["datetime"].isna().any():
                    current.loc[current["datetime"].isna(), "datetime"] = pd.to_datetime(
                        dt_str[current["datetime"].isna()],
                        errors="coerce",
                        dayfirst=True,
                        infer_datetime_format=True,
                    )
            else:
                # Fallbacks supplémentaires: essayer de parser la colonne Date seule comme datetime
                parsed = False
                if dcol:
                    try:
                        current["datetime"] = pd.to_datetime(current[dcol].astype(str).str.strip(), errors="coerce", dayfirst=True, infer_datetime_format=True)
                        parsed = True
                    except Exception:
                        parsed = False
                # Sinon tenter de détecter une colonne candidate en scannant toutes les colonnes texte
                if not parsed:
                    for cand in current.columns:
                        s = current[cand].astype(str).str.strip()
                        # Heuristique: contient un chiffre et un séparateur de date ou un 'T'
                        if s.str.contains(r"(\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}|T\d{2}:\d{2})", regex=True, na=False).mean() > 0.5:
                            dt_try = pd.to_datetime(s, errors="coerce", dayfirst=True, infer_datetime_format=True, utc=False)
                            if dt_try.notna().mean() > 0.5:
                                current["datetime"] = dt_try
                                parsed = True
                                break
                if not parsed:
                    raise ValueError("Colonnes date/heure introuvables dans le CSV (attendues: Datum/Date et Zeit/Time ou une colonne 'DateTime/Timestamp').")

            # Filtrer lignes invalides
            invalid_count = int(current["datetime"].isna().sum())
            if invalid_count and verbose>0:
                print(f"Ignored {invalid_count} rows with invalid datetime in {filename}")
            current = current.dropna(subset=['datetime'])

            # ... existing code ...
            current = current.sort_values(['datetime'],ascending = [True]) # type: ignore
            for col_name in dico:
                if col_name in current.columns:
                    current=current.rename(columns={col_name:dico[col_name]}) # type: ignore
            current = current.replace(',', '.', regex=True)

            # Ne garder que les lignes du jour correspondant au fichier
            current = current[current['datetime'].dt.date == current_date]

            # Assurer la présence des colonnes ECS, sinon valeur par défaut 0
            for col in ['T°C ECS', 'T°C ECS (arret)', 'T°C ECS Consigne', 'Circulateur ECS', 'Status ESC']:
                if col not in current.columns:
                    current[col] = 0

            # Construire les objets puis insertion par lot
            objs = []
            for idx in current.index:
                if verbose>0 and (idx % 1000 == 0):
                    print(f"building row {idx}    ", end='\r')
                datetime_c = make_aware(current.loc[idx,'datetime'])
                objs.append(
                    RawData(
                        datetime = datetime_c,
                        ext_temp = current.loc[idx,'T°C Extérieure'] if 'T°C Extérieure' in current.columns else None,
                        house_temp = current.loc[idx,'T°C Ambiante'] if 'T°C Ambiante' in current.columns else None,
                        house_temp_target = current.loc[idx,'T°C Ambiante Consigne'] if 'T°C Ambiante Consigne' in current.columns else None,
                        silo_level = current.loc[idx,'Niveau Sillo kg'] if 'Niveau Sillo kg' in current.columns else None,
                        hopper_level = current.loc[idx,'Niveau tremis kg'] if 'Niveau tremis kg' in current.columns else None,
                        boiler_water_temp = current.loc[idx,'T°C Chaudière'] if 'T°C Chaudière' in current.columns else None,
                        boiler_water_temp_target = current.loc[idx,'T°C Chaudière Consigne'] if 'T°C Chaudière Consigne' in current.columns else None,
                        boiler_modulation = current.loc[idx,'PE1 Modulation[%]'] if 'PE1 Modulation[%]' in current.columns else None,
                        boiler_fire_temps = current.loc[idx,'T°C Flamme'] if 'T°C Flamme' in current.columns else None,
                        boiler_fire_temps_atrget = current.loc[idx,'T°C Flamme Consigne'] if 'T°C Flamme Consigne' in current.columns else None,
                        heating_start_circulation_temp = current.loc[idx,'T°C Départ'] if 'T°C Départ' in current.columns else None,
                        heating_start_circulation_temp_target = current.loc[idx,'T°C Départ Consigne'] if 'T°C Départ Consigne' in current.columns else None,
                        heating_circulation = current.loc[idx,'Circulateur Chauffage (On/Off)'] if 'Circulateur Chauffage (On/Off)' in current.columns else None,
                        heating_status = current.loc[idx,'Status Chauff.'] if 'Status Chauff.' in current.columns else None,
                        water_temp = current.loc[idx,'T°C ECS'] if 'T°C ECS' in current.columns else None,
                        water_stop_temp = current.loc[idx,'T°C ECS (arret)'] if 'T°C ECS (arret)' in current.columns else None,
                        water_temp_target = current.loc[idx,'T°C ECS Consigne'] if 'T°C ECS Consigne' in current.columns else None,
                        water_circulation = current.loc[idx,'Circulateur ECS'] if 'Circulateur ECS' in current.columns else None,
                        water_status = current.loc[idx,'Status ESC'] if 'Status ESC' in current.columns else None,
                    )
                )

            if objs:
                if verbose>0:
                    print(f"\nBulk inserting {len(objs)} rows (batch_size={batch_size})…")
                RawData.objects.bulk_create(objs, batch_size=batch_size, ignore_conflicts=True)
        print("")