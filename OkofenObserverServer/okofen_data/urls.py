from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("daydata/<int:year>/<int:month>/<int:day>/graph/", views.daygraph, name="daygraph"),
]