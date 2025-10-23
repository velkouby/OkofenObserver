from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Iterable

import pandas as pd
from django.db import transaction
from django.utils import timezone as djtz

from okofen_data import data_api
from okofen_data.models import DailyStat, RawData


@dataclass(frozen=True)
class DayWindow:
    day: date
    start: datetime
    end: datetime


def _make_day_window(day: date) -> DayWindow:
    start_naive = datetime(day.year, day.month, day.day, 3, 0, 0)
    tz = djtz.get_current_timezone()
    start = djtz.make_aware(start_naive, timezone=tz) if djtz.is_naive(start_naive) else start_naive
    end = start + timedelta(days=1)
    return DayWindow(day=day, start=start, end=end)


def _duration_boiler_on_sec(df: pd.DataFrame, threshold_c: float = 200.0) -> float:
    if df.empty or 'T°C Flamme' not in df.columns:
        return 0.0
    dfi = df[['T°C Flamme']].dropna().sort_index()
    if dfi.empty:
        return 0.0
    idx = dfi.index.to_series()
    dt = idx.shift(-1) - idx
    dt_sec = dt.dt.total_seconds().fillna(0)
    status = (dfi['T°C Flamme'] >= threshold_c).astype(float)
    return float((dt_sec * status).sum())


def _sum_descents(series: pd.Series) -> float:
    if series is None:
        return 0.0
    s = series.dropna()
    if s.empty:
        return 0.0
    diffs = s.diff()
    consumed = -diffs[diffs < 0].sum()
    return float(consumed) if consumed == consumed else 0.0


def _time_window_mean(df: pd.DataFrame, colname: str, start: datetime, end: datetime) -> float | None:
    if df.empty or colname not in df.columns:
        return None
    window = df.loc[(df.index >= start) & (df.index < end)]
    if window.empty:
        return None
    s = window[colname].dropna()
    return float(s.mean()) if not s.empty else None


def _heating_mask(df: pd.DataFrame) -> pd.Series | None:
    if df.empty:
        return None
    if 'Status Chauff.' in df.columns:
        mask = df['Status Chauff.'].fillna(0) > 0
        return mask if mask.any() else None
    if 'T°C Départ Consigne' in df.columns:
        mask = df['T°C Départ Consigne'].fillna(0) > 0
        return mask if mask.any() else None
    if 'Circulateur Chauffage (On/Off)' in df.columns:
        mask = df['Circulateur Chauffage (On/Off)'].fillna(0) > 0
        return mask if mask.any() else None
    return None


def _heating_mean(df: pd.DataFrame, colname: str, mask: pd.Series | None) -> float | None:
    if df.empty or colname not in df.columns:
        return None
    if mask is not None:
        s = df.loc[mask, colname].dropna()
        if not s.empty:
            return float(s.mean())
    s = df[colname].dropna()
    return float(s.mean()) if not s.empty else None


def _ecs_means(df: pd.DataFrame) -> tuple[float | None, float | None]:
    if df.empty or 'T°C ECS' not in df.columns:
        return None, None
    global_series = df['T°C ECS'].dropna()
    global_mean = float(global_series.mean()) if not global_series.empty else None
    if 'T°C ECS Consigne' not in df.columns:
        return None, global_mean
    ecs_mask = df['T°C ECS Consigne'].fillna(0) > 40.0
    if not ecs_mask.any():
        return None, global_mean
    heating_series = df.loc[ecs_mask, 'T°C ECS'].dropna()
    heating_mean = float(heating_series.mean()) if not heating_series.empty else None
    return heating_mean, global_mean


def _fetch_dataframe(window: DayWindow) -> pd.DataFrame:
    qs = RawData.objects.filter(datetime__gte=window.start, datetime__lt=window.end).order_by('datetime')
    objs = list(qs)
    if not objs:
        return pd.DataFrame()
    df = data_api.get_values(objs)
    return df.sort_index()


@transaction.atomic
def compute_and_store_for_day(day: date) -> DailyStat | None:
    window = _make_day_window(day)
    df = _fetch_dataframe(window)
    samples = int(df.shape[0]) if not df.empty else 0
    defaults = {
        'window_start': window.start,
        'window_end': window.end,
        'samples_count': samples,
        'boiler_on_seconds': 0.0,
        'pellet_consumed_kg': 0.0,
        'ext_temp_mean': None,
        'ext_temp_night_mean': None,
        'boiler_water_temp_mean': None,
        'depart_temp_mean': None,
        'ambiante_temp_mean': None,
        'ambiante_temp_night_mean': None,
        'ecs_temp_heat_mean': None,
        'ecs_temp_global_mean': None,
    }

    if df.empty:
        DailyStat.objects.update_or_create(day=day, defaults=defaults)
        return DailyStat.objects.get(day=day)

    heating_mask = _heating_mask(df)
    night_start = window.start
    night_end = night_start + timedelta(hours=2)

    defaults.update({
        'boiler_on_seconds': _duration_boiler_on_sec(df),
        'pellet_consumed_kg': _sum_descents(df['Niveau tremis kg']) if 'Niveau tremis kg' in df.columns else 0.0,
        'ext_temp_mean': _heating_mean(df, 'T°C Extérieure', heating_mask),
        'ext_temp_night_mean': _time_window_mean(df, 'T°C Extérieure', night_start, night_end),
        'boiler_water_temp_mean': _heating_mean(df, 'T°C Chaudière', heating_mask),
        'depart_temp_mean': _heating_mean(df, 'T°C Départ', heating_mask),
        'ambiante_temp_mean': _heating_mean(df, 'T°C Ambiante', heating_mask),
        'ambiante_temp_night_mean': _time_window_mean(df, 'T°C Ambiante', night_start, night_end),
    })

    ecs_heat_mean, ecs_global_mean = _ecs_means(df)
    defaults['ecs_temp_heat_mean'] = ecs_heat_mean
    defaults['ecs_temp_global_mean'] = ecs_global_mean

    DailyStat.objects.update_or_create(day=day, defaults=defaults)
    return DailyStat.objects.get(day=day)


def compute_for_days(days: Iterable[date], *, skip_existing: bool = False) -> list[DailyStat]:
    unique_days = sorted({d for d in days if d is not None})
    results: list[DailyStat] = []
    for day in unique_days:
        if skip_existing and DailyStat.objects.filter(day=day).exists():
            continue
        stat = compute_and_store_for_day(day)
        if stat is not None:
            results.append(stat)
    return results


def recompute_all() -> list[DailyStat]:
    qs = RawData.objects.order_by('datetime')
    first = qs.first()
    last = qs.last()
    if not first or not last:
        DailyStat.objects.all().delete()
        return []
    tz_last = djtz.localtime(last.datetime)
    day_end = (tz_last - timedelta(hours=3)).date()
    tz_first = djtz.localtime(first.datetime)
    day_start = (tz_first - timedelta(hours=3)).date()
    days = [day_start + timedelta(days=i) for i in range((day_end - day_start).days + 1)]
    return compute_for_days(days)


def cleanup_duplicates(days: Iterable[date] | None = None) -> int:
    if days is not None:
        target_days = sorted({d for d in days if d is not None})
    else:
        target_days = list(
            DailyStat.objects.order_by('day').values_list('day', flat=True).distinct()
        )

    removed = 0
    for day in target_days:
        qs = DailyStat.objects.filter(day=day).order_by('-updated_at', '-id')
        keep = qs.first()
        duplicates = qs[1:]
        dup_ids = [obj.id for obj in duplicates]
        if dup_ids:
            DailyStat.objects.filter(id__in=dup_ids).delete()
            removed += len(dup_ids)
        if keep is None and not DailyStat.objects.filter(day=day).exists():
            # If all records were duplicates and deleted, ensure we leave the table clean
            continue
    return removed
