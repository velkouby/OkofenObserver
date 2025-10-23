import json
from datetime import datetime, timedelta
from typing import Sequence

from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone as djtz

from okofen_data.models import DailyStat

import okofen_data.data_api as api

def _format_duration(seconds: float | None) -> str:
    if seconds is None or seconds <= 0:
        return "0:00"
    mins, sec = divmod(int(seconds), 60)
    hrs, mins = divmod(mins, 60)
    return f"{hrs:d}:{mins:02d}"


def _mean_attr(stats: Sequence[DailyStat], attr: str) -> float | None:
    values = [getattr(stat, attr) for stat in stats if getattr(stat, attr) is not None]
    if not values:
        return None
    return float(sum(values) / len(values))


def _period_bounds(stats: Sequence[DailyStat]):
    if not stats:
        return None, None
    start = stats[-1].window_start
    end = stats[0].window_end
    return start, end


def _build_summary(stats: Sequence[DailyStat]):
    count = len(stats)
    range_start, range_end = _period_bounds(stats)
    boiler_sec = _mean_attr(stats, 'boiler_on_seconds')
    pellet_avg = _mean_attr(stats, 'pellet_consumed_kg')
    heating = {
        'temp_ambiante_moy': _mean_attr(stats, 'ambiante_temp_mean'),
        'temp_ambiante_nuit': _mean_attr(stats, 'ambiante_temp_night_mean'),
        'temp_depart_moy': _mean_attr(stats, 'depart_temp_mean'),
        'temp_ext_moy': _mean_attr(stats, 'ext_temp_mean'),
        'temp_ext_nuit': _mean_attr(stats, 'ext_temp_night_mean'),
        'temp_chaudiere_moy': _mean_attr(stats, 'boiler_water_temp_mean'),
    }
    ecs = {
        'temp_ecs_chauffe_moy': _mean_attr(stats, 'ecs_temp_heat_mean'),
        'temp_ecs_global_moy': _mean_attr(stats, 'ecs_temp_global_mean'),
    }
    return {
        'has_data': count > 0,
        'count': count,
        'range_start': range_start,
        'range_end': range_end,
        'boiler_on_seconds': boiler_sec,
        'boiler_on_hours': (boiler_sec / 3600.0) if boiler_sec is not None else None,
        'boiler_on_duration': _format_duration(boiler_sec),
        'pellet_consumed_kg': pellet_avg,
        'heating': heating,
        'ecs': ecs,
    }


def _chart_data(stats: Sequence[DailyStat]) -> dict:
    if not stats:
        return {
            'labels': [],
            'chaudiere': {'boiler_hours': [], 'pellet_consumed': []},
            'chauffage': {},
            'ecs': {},
        }

    labels = [stat.day.strftime('%d/%m') for stat in stats]

    def _values(attr: str, transform=None):
        data = []
        for stat in stats:
            value = getattr(stat, attr)
            if value is None:
                data.append(None)
            else:
                data.append(transform(value) if transform else float(value))
        return data

    chauffage = {
        'temp_ext_moy': _values('ext_temp_mean'),
        'temp_ext_nuit': _values('ext_temp_night_mean'),
        'temp_chaudiere_moy': _values('boiler_water_temp_mean'),
        'temp_depart_moy': _values('depart_temp_mean'),
        'temp_ambiante_moy': _values('ambiante_temp_mean'),
        'temp_ambiante_nuit': _values('ambiante_temp_night_mean'),
    }

    ecs = {
        'temp_ecs_chauffe_moy': _values('ecs_temp_heat_mean'),
        'temp_ecs_global_moy': _values('ecs_temp_global_mean'),
    }

    chaudiere = {
        'boiler_hours': _values('boiler_on_seconds', lambda s: round(s / 3600.0, 2)),
        'pellet_consumed': _values('pellet_consumed_kg', lambda x: round(x, 2)),
    }

    return {
        'labels': labels,
        'chaudiere': chaudiere,
        'chauffage': chauffage,
        'ecs': ecs,
    }


def index(request):
    recent_stats_desc = list(DailyStat.objects.filter(samples_count__gt=0).order_by('-day')[:30])
    day_summary = _build_summary(recent_stats_desc[:1])
    week_summary = _build_summary(recent_stats_desc[:7])
    month_summary = _build_summary(recent_stats_desc[:30])

    summary_tabs = [
        {'id': 'day', 'label': "Aujourd'hui", 'summary': day_summary},
        {'id': 'week', 'label': 'Semaine', 'summary': week_summary},
        {'id': 'month', 'label': 'Mois', 'summary': month_summary},
    ]

    chart_stats = list(reversed(recent_stats_desc))
    chart_data = _chart_data(chart_stats)

    chart_range_start = chart_stats[0].day if chart_stats else None
    chart_range_end = chart_stats[-1].day if chart_stats else None

    context = {
        'summary_tabs': summary_tabs,
        'chart_data_json': json.dumps(chart_data, ensure_ascii=False, cls=DjangoJSONEncoder),
        'chart_range_start': chart_range_start,
        'chart_range_end': chart_range_end,
        'latest_update': recent_stats_desc[0].updated_at if recent_stats_desc else None,
    }
    return render(request, "okofen_data/home.html", context)

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
