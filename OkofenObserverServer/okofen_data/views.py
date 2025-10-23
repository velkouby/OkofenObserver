from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from datetime import datetime, timedelta
import okofen_data.data_api as api

def index(request):
    return HttpResponse("Hello, world. You're at the polls index.")

def daygraph(request, year:int, month:int,day:int):
    date = datetime(year=year,month=month,day=day)
    df = api.get_data_for_one_day(date)
    response = f"Data for {year}/{month}/{day}:\n\n" + str(df)
    return HttpResponse(response )


def _df_to_records(df):
    if df is None or df.empty:
        return []
    d2 = df.reset_index().copy()
    # Normalise datetime to ISO 8601 strings
    d2['datetime'] = d2['datetime'].apply(lambda d: d.isoformat())
    return d2.to_dict(orient='records')


def dayjson(request, year: int, month: int, day: int):
    date = datetime(year=year, month=month, day=day)
    df = api.get_data_for_one_day(date)
    records = _df_to_records(df)
    return JsonResponse({"count": len(records), "data": records})


def rangejson(request, start: str, end: str):
    """Return JSON for inclusive date range [start, end] at day granularity.
    Dates must be in YYYY-MM-DD format.
    The day window starts at 03:00 (as per data_api convention).
    """
    try:
        start_d = datetime.strptime(start, "%Y-%m-%d")
        end_d = datetime.strptime(end, "%Y-%m-%d")
    except ValueError:
        return JsonResponse({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)

    start_dt = api.get_start_day_datetime(start_d)
    end_dt = api.get_start_day_datetime(end_d) + timedelta(days=1)
    df = api.get_data_by_dates(start_dt, end_dt)
    records = _df_to_records(df)
    return JsonResponse({"count": len(records), "data": records, "start": start, "end": end})


def lastdaysjson(request, days: int):
    if days <= 0:
        return JsonResponse({"error": "days must be > 0"}, status=400)
    df = api.get_data_for_n_last_days(days)
    records = _df_to_records(df)
    return JsonResponse({"count": len(records), "data": records, "days": days})
