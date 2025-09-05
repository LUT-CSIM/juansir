from django.contrib import admin

from .models import (
    DiseaseType,
    WeatherType,
    SeverityLevel,
    ReportType,
    MediaType,
    DetectionBatch,
    Report,
    DefectTrack,
    DiseaseMedia,
    GroundTruthFrame,
)


@admin.register(DiseaseType)
class DiseaseTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name",)


@admin.register(WeatherType)
class WeatherTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "code")
    search_fields = ("name", "code")


@admin.register(SeverityLevel)
class SeverityLevelAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "description")
    search_fields = ("name", "code")


@admin.register(ReportType)
class ReportTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "code")
    search_fields = ("name", "code")


@admin.register(MediaType)
class MediaTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "code")
    search_fields = ("name", "code")


@admin.register(DetectionBatch)
class DetectionBatchAdmin(admin.ModelAdmin):
    list_display = ("airport", "start_time", "drone_id", "weather", "status")
    list_filter = ("status", "weather")
    search_fields = ("airport", "drone_id")


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("batch", "report_type", "generated_at")
    list_filter = ("report_type",)
    search_fields = ("batch__airport",)


@admin.register(DefectTrack)
class DefectTrackAdmin(admin.ModelAdmin):
    list_display = (
        "unique_code",
        "disease_type",
        "batch",
        "severity",
        "start_frame",
        "end_frame",
    )
    list_filter = ("disease_type", "severity")
    search_fields = ("unique_code",)


@admin.register(DiseaseMedia)
class DiseaseMediaAdmin(admin.ModelAdmin):
    list_display = ("defect_track", "media_type", "file_link")
    list_filter = ("media_type",)
    search_fields = ("defect_track__unique_code",)


@admin.register(GroundTruthFrame)
class GroundTruthFrameAdmin(admin.ModelAdmin):
    list_display = ("track", "frame_index", "time")
    list_filter = ("track",)
