from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("api/stats/", views.dashboard_stats, name="stats"),
    path("api/disease_types/", views.disease_type_stats, name="disease_type_stats"),
    path("api/batches/", views.detection_batches, name="batches"),
    path("api/boxes/", views.anomaly_boxes, name="anomaly_boxes"),
    path("api/tracks/", views.defect_tracks, name="defect_tracks"),
    path("api/road_stats/", views.road_stats, name="road_stats"),
    path("api/weather/", views.current_weather, name="current_weather"),
]
