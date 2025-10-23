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
            current['datetime']=pd.to_datetime(current['Datum ']+' '+current['Zeit '],format="%d.%m.%Y %H:%M:%S")
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
                        ext_temp = current.loc[idx,'T°C Extérieure'],
                        house_temp = current.loc[idx,'T°C Ambiante'],
                        house_temp_target = current.loc[idx,'T°C Ambiante Consigne'],
                        silo_level = current.loc[idx,'Niveau Sillo kg'],
                        hopper_level = current.loc[idx,'Niveau tremis kg'],
                        boiler_water_temp = current.loc[idx,'T°C Chaudière'],
                        boiler_water_temp_target = current.loc[idx,'T°C Chaudière Consigne'],
                        boiler_modulation = current.loc[idx,'PE1 Modulation[%]'],
                        boiler_fire_temps = current.loc[idx,'T°C Flamme'],
                        boiler_fire_temps_atrget = current.loc[idx,'T°C Flamme Consigne'],
                        heating_start_circulation_temp = current.loc[idx,'T°C Départ'],
                        heating_start_circulation_temp_target = current.loc[idx,'T°C Départ Consigne'],
                        heating_circulation = current.loc[idx,'Circulateur Chauffage (On/Off)'],
                        heating_status = current.loc[idx,'Status Chauff.'],
                        water_temp = current.loc[idx,'T°C ECS'],
                        water_stop_temp = current.loc[idx,'T°C ECS (arret)'],
                        water_temp_target = current.loc[idx,'T°C ECS Consigne'],
                        water_circulation = current.loc[idx,'Circulateur ECS'],
                        water_status = current.loc[idx,'Status ESC'],
                    )
                )

            if objs:
                if verbose>0:
                    print(f"\nBulk inserting {len(objs)} rows (batch_size={batch_size})…")
                RawData.objects.bulk_create(objs, batch_size=batch_size, ignore_conflicts=True)
        print("")
