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