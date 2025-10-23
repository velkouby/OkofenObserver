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
