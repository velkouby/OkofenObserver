import json
from datetime import datetime, timedelta

from django.http import JsonResponse
from django.shortcuts import redirect, render

import okofen_data.data_api as api

def index(request):
    return redirect("graph_explorer")

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


def graph_explorer(request):
    metrics = [
        {
            "key": "T°C Ambiante Consigne",
            "label": "Consigne température ambiante",
            "default": True,
            "color": "#2b8cf3",
        },
        {
            "key": "T°C Ambiante",
            "label": "Température ambiante",
            "default": True,
            "color": "#f37f2b",
        },
        {
            "key": "T°C Extérieure",
            "label": "Température extérieure",
            "default": False,
            "color": "#10b981",
        },
        {
            "key": "T°C Chaudière",
            "label": "Température chaudière",
            "default": False,
        },
        {
            "key": "T°C Chaudière Consigne",
            "label": "Consigne chaudière",
            "default": False,
        },
        {
            "key": "PE1 Modulation[%]",
            "label": "Modulation chaudière",
            "default": False,
        },
        {
            "key": "T°C Flamme",
            "label": "Température flamme",
            "default": False,
        },
        {
            "key": "T°C Départ",
            "label": "Température départ chauffage",
            "default": False,
        },
        {
            "key": "T°C Départ Consigne",
            "label": "Consigne départ chauffage",
            "default": False,
        },
        {
            "key": "T°C ECS",
            "label": "Température ECS",
            "default": False,
        },
        {
            "key": "T°C ECS Consigne",
            "label": "Consigne ECS",
            "default": False,
        },
        {
            "key": "Niveau Sillo kg",
            "label": "Niveau silo",
            "default": False,
        },
        {
            "key": "Niveau tremis kg",
            "label": "Niveau trémie",
            "default": False,
        },
        {
            "key": "Circulateur Chauffage (On/Off)",
            "label": "Circulateur chauffage",
            "default": False,
        },
        {
            "key": "Circulateur ECS",
            "label": "Circulateur ECS",
            "default": False,
        },
        {
            "key": "Status Chauff.",
            "label": "Statut chauffage",
            "default": False,
        },
        {
            "key": "Status ESC",
            "label": "Statut ECS",
            "default": False,
        },
    ]

    metrics_config = {
        metric["key"]: metric for metric in metrics
    }

    context = {
        "metrics_config": json.dumps(metrics_config, ensure_ascii=False),
    }
    return render(request, "okofen_data/graph_explorer.html", context)
