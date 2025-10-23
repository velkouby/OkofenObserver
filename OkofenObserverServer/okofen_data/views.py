import json
from datetime import datetime, timedelta

from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone as djtz

from okofen_data.models import RawData

import okofen_data.data_api as api

def _format_duration(seconds: float) -> str:
    if seconds is None or seconds <= 0:
        return "0:00"
    mins, sec = divmod(int(seconds), 60)
    hrs, mins = divmod(mins, 60)
    return f"{hrs:d}:{mins:02d}"


def _compute_last_complete_day_dataframe():
    """Return dataframe for the last complete day based on available data.

    Day window is [D 03:00, D+1 03:00). We pick the window immediately
    preceding the day that contains the latest data point.
    """
    last = RawData.objects.order_by('-datetime').first()
    if not last:
        return None, None, None
    # Work in project-local timezone, then drop tzinfo to align with data_api
    last_local = djtz.localtime(last.datetime)
    last_naive = last_local.replace(tzinfo=None)
    start_current = api.get_start_day_datetime(last_naive)
    # If timestamp is before 03:00, it belongs to previous window
    if last_naive < start_current:
        start_current = start_current - timedelta(days=1)
    # Last complete day is the window just before the current window
    start_dt = start_current - timedelta(days=1)
    end_dt = start_current
    df = api.get_data_by_dates(start_dt, end_dt)
    return df, start_dt, end_dt


def _duration_boiler_on_sec(df, threshold_c=200.0) -> float:
    """Compute total duration in seconds where flame temp >= threshold.

    We assume status for interval [t_i, t_{i+1}) equals status at t_i.
    """
    if df is None or df.empty or 'T°C Flamme' not in df.columns:
        return 0.0
    dfi = df.copy()
    dfi = dfi.dropna(subset=['T°C Flamme'])
    if dfi.empty:
        return 0.0
    idx = dfi.index.to_series().sort_values()
    # durations between consecutive samples
    dt = idx.shift(-1) - idx
    dt_sec = dt.dt.total_seconds().fillna(0)
    status = (dfi['T°C Flamme'] >= threshold_c).astype(int)
    # Align dt_sec to same index
    on_dt_sec = dt_sec * status
    return float(on_dt_sec.sum())


def _sum_descents(series) -> float:
    """Sum of all decreases over the series (positive kg consumed)."""
    if series is None:
        return 0.0
    s = series.dropna()
    if s.empty:
        return 0.0
    diffs = s.diff()
    # Negative diffs represent consumption (level decreased)
    consumed = -diffs[diffs < 0].sum()
    return float(consumed) if consumed == consumed else 0.0  # handle NaN


def _time_window_mean(df, colname: str, start: datetime, end: datetime):
    if df is None or df.empty or colname not in df.columns:
        return None
    # Align timezone awareness for comparisons
    try:
        index_tz = getattr(df.index, 'tz', None)
        if index_tz is not None:
            if start.tzinfo is None:
                start = djtz.make_aware(start)
            if end.tzinfo is None:
                end = djtz.make_aware(end)
    except Exception:
        pass
    window = df.loc[(df.index >= start) & (df.index < end)]
    if window.empty:
        return None
    s = window[colname].dropna()
    return float(s.mean()) if not s.empty else None


def index(request):
    # Compute dashboard metrics for the last complete day of data
    df, start_dt, end_dt = _compute_last_complete_day_dataframe()

    # Boiler on-time based on flame temp threshold
    boiler_on_sec = _duration_boiler_on_sec(df, threshold_c=200.0)

    # Pellet consumption (kg) from trémie level decreases
    hopper_key = 'Niveau tremis kg'
    pellet_consumed = _sum_descents(df[hopper_key]) if (df is not None and not df.empty and hopper_key in df.columns) else 0.0

    # Heating consigne periods mask
    heating_mask = None
    if df is not None and not df.empty:
        if 'Status Chauff.' in df.columns:
            heating_mask = df['Status Chauff.'] > 0
        elif 'T°C Départ Consigne' in df.columns:
            # Fallback: consider consigne periods when a non-zero target exists
            heating_mask = df['T°C Départ Consigne'].fillna(0) > 0
        elif 'Circulateur Chauffage (On/Off)' in df.columns:
            heating_mask = df['Circulateur Chauffage (On/Off)'].fillna(0) > 0

    def _masked_mean(colname):
        if df is None or df.empty or colname not in df.columns:
            return None
        s = df[colname].dropna()
        if s.empty:
            return None
        if heating_mask is not None and heating_mask.any():
            s = df.loc[heating_mask, colname].dropna()
        return float(s.mean()) if not s.empty else None

    heating_stats = {
        'temp_ext_moy': _masked_mean('T°C Extérieure'),
        'temp_chaudiere_moy': _masked_mean('T°C Chaudière'),
        'temp_depart_moy': _masked_mean('T°C Départ'),
        'temp_ambiante_moy': _masked_mean('T°C Ambiante'),
    }

    # ECS: averages
    def _daily_mean(colname):
        if df is None or df.empty or colname not in df.columns:
            return None
        s = df[colname].dropna()
        return float(s.mean()) if not s.empty else None

    ecs_mask = None
    if df is not None and not df.empty and 'T°C ECS Consigne' in df.columns:
        ecs_mask = df['T°C ECS Consigne'].fillna(0) > 40.0
    def _ecs_heating_mean():
        if df is None or df.empty or 'T°C ECS' not in df.columns:
            return None
        if ecs_mask is None or not ecs_mask.any():
            return None
        s = df.loc[ecs_mask, 'T°C ECS'].dropna()
        return float(s.mean()) if not s.empty else None

    ecs_stats = {
        'temp_ecs_chauffe_moy': _ecs_heating_mean(),
        'temp_ecs_global_moy': _daily_mean('T°C ECS'),
    }

    # Night ambient temperature mean between 03:00 and 05:00
    night_start = start_dt
    night_end = start_dt + timedelta(hours=2)
    night_ambiante_moy = _time_window_mean(df, 'T°C Ambiante', night_start, night_end)
    night_ext_moy = _time_window_mean(df, 'T°C Extérieure', night_start, night_end)

    context = {
        'day_start': start_dt,
        'day_end': end_dt,
        'boiler_on_duration': _format_duration(boiler_on_sec),
        'boiler_on_seconds': int(boiler_on_sec),
        'pellet_consumed_kg': round(pellet_consumed, 2) if pellet_consumed is not None else None,
        'heating_stats': heating_stats,
        'ecs_stats': ecs_stats,
        'night_ambiante_moy': night_ambiante_moy,
        'night_ext_moy': night_ext_moy,
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
