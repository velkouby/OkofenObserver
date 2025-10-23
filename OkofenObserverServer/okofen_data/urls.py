from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("daydata/<int:year>/<int:month>/<int:day>/graph/", views.daygraph, name="daygraph"),
    path("daydata/<int:year>/<int:month>/<int:day>/json/", views.dayjson, name="dayjson"),
    path("range/<str:start>/<str:end>/json/", views.rangejson, name="rangejson"),
    path("lastdays/<int:days>/json/", views.lastdaysjson, name="lastdaysjson"),
]
