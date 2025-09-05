"""Views for the web app."""

from itertools import groupby
from operator import attrgetter

from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import render
from django.conf import settings

from .models import (
    DetectionBatch,
    DefectTrack,
    GroundTruthFrame,
    DiseaseMedia,
)


def index(request):
    """Render the dashboard landing page."""
    return render(request, "web/index.html")


def dashboard_stats(request):
    """Return simple dashboard statistics.

    If a ``batch`` query parameter is supplied the response will also include
    statistics for that specific :class:`DetectionBatch` under the ``batch``
    key.
    """

    inspection_count = DetectionBatch.objects.count()
    total = DefectTrack.objects.count()
    completed = DefectTrack.objects.filter(develop_trend="已修复").count()
    pending = total - completed
    rate = round((completed / total * 100) if total else 0, 2)

    data = {
        "inspection_count": inspection_count,
        "pending_count": pending,
        "completion_rate": rate,
    }

    batch_id = request.GET.get("batch")
    if batch_id:
        qs = DefectTrack.objects.filter(batch_id=batch_id)
        b_total = qs.count()
        b_completed = qs.filter(develop_trend="已修复").count()
        b_pending = b_total - b_completed
        b_rate = round((b_completed / b_total * 100) if b_total else 0, 2)
        data["batch"] = {
            "defect_count": b_total,
            "pending_count": b_pending,
            "completion_rate": b_rate,
        }

    return JsonResponse(data)


def disease_type_stats(request):
    """Return distribution of disease types."""
    qs = (
        DefectTrack.objects.values("disease_type__name")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    labels = [i["disease_type__name"] for i in qs]
    data = [i["count"] for i in qs]
    return JsonResponse({"labels": labels, "data": data})


def detection_batches(request):
    """Return recent detection batches."""
    batches = [
        {"id": b.id, "name": str(b)}
        for b in DetectionBatch.objects.order_by("-start_time")[:5]
    ]
    return JsonResponse({"batches": batches})


def anomaly_boxes(request):
    """Return bounding boxes for anomaly frames."""
    batch_id = request.GET.get("batch")
    qs = GroundTruthFrame.objects.select_related(
        "track__disease_type", "track__batch"
    )
    if batch_id:
        qs = qs.filter(track__batch_id=batch_id)
    qs = qs.order_by("frame_index")
    frames = []
    for frame_index, group in groupby(qs, key=attrgetter("frame_index")):
        group = list(group)
        time = group[0].time
        boxes = [
            {
                "track": g.track_id,
                "x": g.bbox_x,
                "y": g.bbox_y,
                "w": g.bbox_width,
                "h": g.bbox_height,
                "label": g.track.disease_type.name,
                "start": g.track.start_frame,
                "end": g.track.end_frame,
            }
            for g in group
        ]
        frames.append({"frame": frame_index, "time": time, "boxes": boxes})
    video = qs.first().track.batch.video_link if qs else ""
    return JsonResponse({"video": video, "frames": frames})


def defect_tracks(request):
    """Return available defect tracks with snapshot and start time."""
    batch_id = request.GET.get("batch")
    tracks = []
    qs = DefectTrack.objects.select_related("disease_type").prefetch_related("media")
    if batch_id:
        qs = qs.filter(batch_id=batch_id)
    limit = getattr(settings, "TRACK_PREVIEW_LIMIT", 5)
    qs = qs[:limit]
    for t in qs:
        snapshot = t.snapshot_link
        if not snapshot:
            media = next(
                (m for m in t.media.all() if getattr(m.media_type, "code", "") == "image"),
                None,
            )
            if media:
                snapshot = media.file_link
        tracks.append(
            {
                "id": t.id,
                "label": t.disease_type.name,
                "start": t.start_time or 0,
                "snapshot": snapshot or "",
            }
        )
    return JsonResponse({"tracks": tracks})


def road_stats(request):
    """Return total road mileage and count configured in settings."""
    return JsonResponse(
        {
            "total_length": getattr(settings, "ROAD_TOTAL_LENGTH", 0),
            "total_count": getattr(settings, "ROAD_TOTAL_COUNT", 0),
        }
    )


def current_weather(request):
    """Return today's weather and temperature based on latest batch."""
    batch = DetectionBatch.objects.order_by("-start_time").first()
    weather = batch.weather.name if batch and batch.weather else ""
    code = batch.weather.code if batch and batch.weather else ""
    temperature = batch.temperature if batch else None
    return JsonResponse({"weather": weather, "code": code, "temperature": temperature})
