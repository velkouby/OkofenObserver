# Set of instruction for django site creation

* Create root site
django-admin startproject OkofenObserverServer

* Create data application
python manage.py startapp okofen_data

python manage.py makemigrations okofen_data
python manage.py migrate

* Admin site
python manage.py createsuperuser

* python manage.py runserver
  

## Switch to MySQL (install + DB creation)

1) Install MySQL server and client build deps (Debian/Ubuntu)

```
sudo apt-get update
sudo apt-get install -y mysql-server libmysqlclient-dev build-essential python3-dev pkg-config
```

2) Install Python driver

```
pip install --upgrade pip
pip install mysqlclient
```

3) Create database and user

```
sudo mysql -u root
```

In MySQL shell:

```
CREATE DATABASE okofen_observer CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'okofen'@'localhost' IDENTIFIED BY 'strong_pass_here';
GRANT ALL PRIVILEGES ON okofen_observer.* TO 'okofen'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

4) Configure Django settings

`OkofenObserverServer/OkofenObserverServer/settings.py` is set to use MySQL by default with env overrides:

```
ENGINE  = django.db.backends.mysql
NAME    = okofen_observer
USER    = okofen
PASSWORD= okofen_password  # override with env var
HOST    = 127.0.0.1
PORT    = 3306
```

Recommended environment variables (override defaults):

```
export DB_NAME=okofen_observer
export DB_USER=okofen
export DB_PASSWORD=strong_pass_here
export DB_HOST=127.0.0.1
export DB_PORT=3306
```

5) Apply migrations

```
cd OkofenObserverServer
python manage.py makemigrations
python manage.py migrate
```

6) Create admin user (if needed) and run server

```
python manage.py createsuperuser
python manage.py runserver
```

Notes:
- Ensure MySQL is running: `sudo systemctl status mysql` (start with `sudo systemctl start mysql`).
- If you want to temporarily use SQLite, set `DB_ENGINE=django.db.backends.sqlite3` and `DB_NAME` to a path (e.g. `db.sqlite3`).
