from django.db import models


class RawData(models.Model):
    datetime = models.DateTimeField(verbose_name='datetime',unique=True)
    ext_temp = models.FloatField(verbose_name = 'T°C Extérieure',default=0.)
    house_temp = models.FloatField(verbose_name = 'T°C Ambiante',default=0.)
    house_temp_target = models.FloatField(verbose_name = 'T°C Ambiante Consigne',default=0.)
    silo_level = models.FloatField(verbose_name = 'Niveau Sillo kg',default=0.)
    hopper_level = models.FloatField(verbose_name = 'Niveau tremis kg',default=0.)    
    boiler_water_temp = models.FloatField(verbose_name = 'T°C Chaudière',default=0.)
    boiler_water_temp_target = models.FloatField(verbose_name = 'T°C Chaudière Consigne',default=0.)
    boiler_modulation = models.FloatField(verbose_name = 'PE1 Modulation[%]',default=0.)
    boiler_fire_temps = models.FloatField(verbose_name = 'T°C Flamme',default=0.)
    boiler_fire_temps_atrget = models.FloatField(verbose_name = 'T°C Flamme Consigne',default=0.)
    heating_start_circulation_temp = models.FloatField(verbose_name = 'T°C Départ',default=0.)
    heating_start_circulation_temp_target = models.FloatField(verbose_name = 'T°C Départ Consigne',default=0.)
    heating_circulation = models.FloatField(verbose_name = 'Circulateur Chauffage (On/Off)',default=0.)
    heating_status = models.IntegerField(verbose_name = 'Status Chauff.',default=0.)
    water_temp = models.FloatField(verbose_name = 'T°C ECS',default=0.)
    water_stop_temp = models.FloatField(verbose_name = 'T°C ECS (arret)',default=0.)
    water_temp_target = models.FloatField(verbose_name = 'T°C ECS Consigne',default=0.)
    water_circulation = models.FloatField(verbose_name = 'Circulateur ECS',default=0.)
    water_status = models.IntegerField(verbose_name = 'Status ESC',default=0)


class DailyStat(models.Model):
    day = models.DateField(unique=True)
    window_start = models.DateTimeField()
    window_end = models.DateTimeField()
    samples_count = models.PositiveIntegerField(default=0)
    boiler_on_seconds = models.FloatField(default=0.0)
    pellet_consumed_kg = models.FloatField(default=0.0)
    ext_temp_mean = models.FloatField(null=True, blank=True)
    ext_temp_night_mean = models.FloatField(null=True, blank=True)
    boiler_water_temp_mean = models.FloatField(null=True, blank=True)
    depart_temp_mean = models.FloatField(null=True, blank=True)
    ambiante_temp_mean = models.FloatField(null=True, blank=True)
    ambiante_temp_night_mean = models.FloatField(null=True, blank=True)
    ecs_temp_heat_mean = models.FloatField(null=True, blank=True)
    ecs_temp_global_mean = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-day"]

    def __str__(self) -> str:
        return f"DailyStat({self.day})"
