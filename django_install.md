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
  
