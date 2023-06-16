from okofen_data.models import RawData
from datetime import datetime, timedelta
import pandas as pd
from django.utils.timezone import make_aware

'''
import okofen_data.data_api as api
start_date=datetime(2023, 1, 1)
end_date=datetime(2023,1,30)
df = api.get_data_by_dates(start_date,end_date)
'''    
def get_values(objs:list[RawData])->pd.DataFrame():
    output={'datetime':[] ,
    'T°C Extérieure':[] ,
    'T°C Ambiante':[] ,
    'T°C Ambiante Consigne':[] ,
    'Niveau Sillo kg':[] ,
    'Niveau tremis kg':[] ,  
    'T°C Chaudière':[] ,
    'T°C Chaudière Consigne':[] ,
    'PE1 Modulation[%]':[] ,
    'T°C Flamme':[],
    'T°C Flamme Consigne':[] ,
    'T°C Départ':[] ,
    'T°C Départ Consigne':[] ,
    'Circulateur Chauffage (On/Off)':[] ,
    'Status Chauff.':[] ,
    'T°C ECS':[] ,
    'T°C ECS (arret)':[] ,
    'T°C ECS Consigne':[] ,
    'Circulateur ECS':[] ,
    'Status ESC':[] }
    for obj in objs:
        output['datetime'].append(obj.datetime)
        output['T°C Extérieure'].append(obj.ext_temp)
        output['T°C Ambiante'].append(obj.house_temp)
        output['T°C Ambiante Consigne'].append(obj.house_temp_target)
        output['Niveau Sillo kg'].append(obj.silo_level)
        output['Niveau tremis kg'].append(obj.hopper_level)  
        output['T°C Chaudière'].append(obj.boiler_water_temp)
        output['T°C Chaudière Consigne'].append(obj.boiler_water_temp_target)
        output['PE1 Modulation[%]'].append(obj.boiler_modulation)
        output['T°C Flamme'].append(obj.boiler_fire_temps),
        output['T°C Flamme Consigne'].append(obj.boiler_fire_temps_atrget)
        output['T°C Départ'].append(obj.heating_start_circulation_temp)
        output['T°C Départ Consigne'].append(obj.heating_start_circulation_temp_target)
        output['Circulateur Chauffage (On/Off)'].append(obj.heating_circulation)
        output['Status Chauff.'].append(obj.heating_status)
        output['T°C ECS'].append(obj.water_temp)
        output['T°C ECS (arret)'].append(obj.water_stop_temp)
        output['T°C ECS Consigne'].append(obj.water_temp_target)
        output['Circulateur ECS'].append(obj.water_circulation)
        output['Status ESC'].append(obj.water_status)
    return pd.DataFrame(output).set_index('datetime')

def get_data_by_dates(start_date:datetime,end_date:datetime)->pd.DataFrame:
    objs = RawData.objects.filter(datetime__range=[make_aware(start_date),make_aware(end_date)]).order_by('datetime')
    return get_values(objs)

def get_start_day_datetime(date:datetime)->datetime:
    return datetime(year=date.year, month=date.month, day= date.day, hour=3, minute=0, second=0)

def get_data_for_one_day(date:datetime)->pd.DataFrame:
    start_date = get_start_day_datetime(date)
    end_date   = start_date+timedelta(days=1)
    return get_data_by_dates(start_date,end_date)

def get_data_for_n_last_days(days:int)->pd.DataFrame:
    date = datetime.now()
    end_date = get_start_day_datetime(date)+timedelta(days=1)
    start_date   = end_date-timedelta(days=days)
    return get_data_by_dates(start_date,end_date)


