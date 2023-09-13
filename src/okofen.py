
from src.mailler import EmailConnector
import os
import src.system as s
import pandas as pd
import glob
from datetime import datetime
from datetime import timedelta  
from dataclasses import dataclass
from dateutil import parser
import json
def datetime2str(d):
    return d.strftime("%Y-%m-%d %H:%M:%S")

def parse_date(d):
    return int(d[-4:]),int(d[3:5]),int(d[:2])

def is_bigger_than(d1,d2):
    if d1[0]>d2[0]:
        return 1
    elif d1[0]<d2[0]:
        return -1
    elif d1[1]>d2[1]:
        return 1
    elif d1[1]<d2[1]:
        return -1
    elif d1[2]>d2[2]:
        return 1
    elif d1[2]<d2[2]:
        return -1
    else:
        return 0
    
def find_lastest_date(data):
    if data.shape[0]==0:
        return None
    a = data['Datum '].value_counts()
    dates=list(a[a>1400].index)
    #dates=data['Datum '].unique()
    lastest_date = dates[0]
    for d in dates:
        #print(parse_date(d))
        if is_bigger_than(parse_date(d),parse_date(lastest_date))==1:
            lastest_date =d
    return   parse_date(lastest_date)

def get_date_from_okofen_file(filename):
    b = s.basename(filename).split('_')
    return int(b[1][:4]),int(b[1][4:6]),int(b[1][6:])

def read_okfen_data(filename)->pd.DataFrame|None:
    try:
        return pd.read_csv(filename,sep=';',encoding = "ISO-8859-1")
    except Exception:
        print('')
        print(f'[ERROR] Fail to read {filename}')
        print('')
        return None
    
@dataclass()
class OkofenConfig:
    data_dir:str="Local directory path to save data"
    gmail_acount:str = "your.name@gmail.com"
    gmail_passwd:str='xxxxxxxxxxx'
    email_subject_key_serach:str = 'P0060B5_41F11E'
    gmail_box:str="INBOX"
    
def read_OkofenConfig(filename:str):
    f = open(filename)
    config_data = json.load(f)
    f.close()

    config = OkofenConfig(
        data_dir=config_data["data_dir"],
        gmail_acount=config_data["gmail_acount"],
        gmail_passwd=config_data["gmail_passwd"],
        email_subject_key_serach=config_data["email_subject_key_serach"],
        gmail_box=config_data["gmail_box"],
    )
    return config
    
class Okofen():
    def __init__(self,config:OkofenConfig, verbose:int = 0):
        self.config = config
        self.verbose = verbose
        self.mail_dir = self.config.gmail_box
        self.key_serach = self.config.email_subject_key_serach
        self.data_dir = self.config.data_dir
        self.gmail = EmailConnector(username = self.config.gmail_acount,password = config.gmail_passwd)
        self.gmail.verbose = verbose == 1
        self.local_files = s.ls_files(self.data_dir,'csv',False)
        self.print("Connexion is setup")
        
    def print(self,msg):
        if self.verbose>0:
            print(msg)
        
    def get_attachement_from_okfen_email(self,email_message,existing_files):
        for part in email_message.walk():
            # this part comes from the snipped I don't understand yet... 
            if part.get_content_maintype() == 'multipart':
                continue
            if part.get('Content-Disposition') is None:
                continue
            filename = part.get_filename()
            self.print(f"Attached file: {filename}")
            if bool(filename):
                if filename[:5]!='touch':
                    continue
                if filename in existing_files:
                    self.print(f'Already have {filename} in db')
                    continue
                filePath = os.path.join('/home/velkouby/dev/data/okfen', filename)
                if not os.path.isfile(filePath):
                    with open(filePath, 'wb') as fp:
                        fp.write(part.get_payload(decode=True))
                self.print(f'"{filename}" has been downloaded' )
        
    def download_data_from_gmail(self):       
        if self.gmail.connect_mailbox():
            mail_count = self.gmail.set_directory(self.mail_dir)
            self.print(f'{mail_count} emails in {self.mail_dir}')
            email_ids = self.gmail.search_emails('FROM',self.key_serach)
            self.print(f'{len(email_ids)} found from sender {self.key_serach}')
            for id in email_ids:
                email_message = self.gmail.get_email(id,False)
                self.get_attachement_from_okfen_email(email_message,self.local_files)
            self.gmail.logout_mailbox()
            self.local_files = s.ls_files(self.data_dir,'csv',False)
            
    def get_local_datafile_list(self):
        return glob.glob(s.join(self.data_dir,'touch_*.csv'))
    
    def update_local_db(self):
        db_filename = s.join(self.data_dir,'0-okofen_db-vendome.h5')
        if s.exists(db_filename):
            self.data = pd.read_hdf(db_filename,key='data')
        else:
            data = pd.DataFrame()
        lastes_date_in_db = find_lastest_date(self.data)
        local_files = self.get_local_datafile_list()
        have_new_data = False
        
        for i in range(len(local_files)):
            current_date = get_date_from_okofen_file(local_files[i])
            if lastes_date_in_db is None or is_bigger_than(current_date,lastes_date_in_db)>0:
                self.print(f'***{local_files[i]}***')
                current = read_okfen_data(local_files[i])
                if current is None:
                    continue
                self.data = pd.concat([self.data,current],ignore_index=True) # type: ignore            
                have_new_data = True
        if have_new_data:
            self.data.to_hdf(db_filename,key='data')
            
    def Update_db_from_gmail(self):
        self.download_data_from_gmail()
        self.update_local_db()
        self.data_format()
        self.get_day_list()
        
    def data_format(self):
        self.data['datetime']=pd.to_datetime(self.data['Datum ']+' '+self.data['Zeit '],format="%d.%m.%Y %H:%M:%S")
        self.data = self.data.sort_values(['datetime'],ascending = [True]) # type: ignore
        dico = {
            'datetime':'datetime',
            'AT [°C]': 'T°C Extérieure',
            'ATakt [°C]': 'ATakt [°C]',
            'PE1 KT[°C]': 'T°C Chaudière',
            'PE1 KT_SOLL[°C]': 'T°C Chaudière Consigne',
            'PE1_BR1 ': 'OKO 1 - Contact Brûleur (On/Off)',
            'HK1 VL Ist[°C]': 'T°C Départ',
            'HK1 VL Soll[°C]': 'T°C Départ Consigne',
            'HK1 RT Ist[°C]': 'T°C Ambiante',
            'HK1 RT Soll[°C]': 'T°C Ambiante Consigne',
            'HK1 Pumpe': 'Circulateur Chauffage (On/Off)',
            'HK1 Status':"Status Chauff.",
            'WW1 EinT Ist[°C]':'T°C ECS',
            'WW1 AusT Ist[°C]':'T°C ECS (arret)',
            'WW1 Soll[°C]':'T°C ECS Consigne',
            'WW1 Pumpe':'Circulateur ECS',
            'WW1 Status':'Status ESC',
            'PE1 Modulation[%]':'PE1 Modulation[%]',
            'PE1 FRT Ist[°C]':'T°C Flamme',
            'PE1 FRT Soll[°C]':'T°C Flamme Consigne',
            'PE1 Fuellstand[kg]' : 'Niveau Sillo kg',
            'PE1 Fuellstand ZWB[kg]' : 'Niveau tremis kg',
        }
        for f in self.data.columns:
            if f in dico:
                self.print(f"'{f}' : '{dico[f]}'") # type: ignore
            else:
                self.print(f"'{f}' : ''")
                
        self.data=self.data[dico.keys()].rename(columns=dico) # type: ignore
        self.data = self.data.replace(',','.', regex=True)
        cols = self.data.columns[1:]
        self.data=pd.DataFrame(data = self.data[cols].to_numpy(), index=self.data['datetime'], columns=cols,dtype='float')


    def select_data(self,d:datetime, nb_days = 1):
        first_day = datetime(d.year,d.month,d.day,3,0,0)
        last_day = first_day+timedelta(days=nb_days)
        return self.data.loc[first_day:last_day]
    
    def select_data_by_days(self, start_date:str, end_date:str)->pd.DataFrame:
        start = parser.parse(start_date,dayfirst=True)
        end = parser.parse(end_date,dayfirst=True)
        first_day = datetime(start.year,start.month,start.day,3,0,0)
        last_day = datetime(end.year,end.month,end.day,2,59,59)
        return self.data.loc[first_day:last_day]
    
    def get_day_list(self):
        self.days= []
        for d in self.data.index:
            date = d.date() # type: ignore
            if date not in self.days:
                self.days.append(date)
        return self.days