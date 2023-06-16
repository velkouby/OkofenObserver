from django.shortcuts import render
from django.http import HttpResponse
from datetime import datetime
import okofen_data.data_api as api

def index(request):
    return HttpResponse("Hello, world. You're at the polls index.")

def daygraph(request, year:int, month:int,day:int):
    date = datetime(year=year,month=month,day=day)
    df = api.get_data_for_one_day(date)
    response = f"Data for {year}/{month}/{day}:\n\n" + str(df)
    return HttpResponse(response )

