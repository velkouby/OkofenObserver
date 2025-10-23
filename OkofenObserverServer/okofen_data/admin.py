from datetime import datetime

from django.contrib import admin
from django.db.models.functions import TruncDate, TruncTime
from django.utils.timezone import localtime

from .models import RawData


class RawDataDateFilter(admin.SimpleListFilter):
    title = "Date"
    parameter_name = "date"

    def lookups(self, request, model_admin):
        dates = (
            RawData.objects.annotate(date_only=TruncDate("datetime"))
            .values_list("date_only", flat=True)
            .distinct()
            .order_by("date_only")
        )
        return [
            (date.isoformat(), date.strftime("%d/%m/%Y"))
            for date in dates
            if date is not None
        ]

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            selected_date = datetime.strptime(value, "%Y-%m-%d").date()
            return queryset.filter(datetime__date=selected_date)
        return queryset


class RawDataTimeFilter(admin.SimpleListFilter):
    title = "Heure"
    parameter_name = "time"

    def lookups(self, request, model_admin):
        times = (
            RawData.objects.annotate(time_only=TruncTime("datetime"))
            .values_list("time_only", flat=True)
            .distinct()
            .order_by("time_only")
        )
        return [
            (time.strftime("%H:%M:%S"), time.strftime("%H:%M:%S"))
            for time in times
            if time is not None
        ]

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            selected_time = datetime.strptime(value, "%H:%M:%S").time()
            return queryset.filter(datetime__time=selected_time)
        return queryset


@admin.register(RawData)
class RawDataAdmin(admin.ModelAdmin):
    list_display = ("id", "display_date", "display_time", "display_house_temp")
    list_filter = (RawDataDateFilter, RawDataTimeFilter)
    ordering = ("-datetime",)

    @admin.display(description="Date", ordering="datetime")
    def display_date(self, obj):
        return localtime(obj.datetime).strftime("%d/%m/%Y")

    @admin.display(description="Heure", ordering="datetime")
    def display_time(self, obj):
        return localtime(obj.datetime).strftime("%H:%M:%S")

    @admin.display(description="T°C Ambiante")
    def display_house_temp(self, obj):
        return obj.house_temp
