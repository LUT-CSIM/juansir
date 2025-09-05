# web/management/commands/generate_demo_data.py
from pathlib import Path
import shutil
import numpy as np
import imageio
import cv2
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.apps import apps
from django.db import connection
from django.conf import settings

from web.models import (
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


class Command(BaseCommand):
    help = "Generate demo detection data with a short video and sample defects"

    # ---------- 1. 生成视频及缺陷标签 ----------
    def _generate_demo_video_with_defects(self, path: Path, duration: int = 10, fps: int = 30):
        width, height = 1920, 1080
        total_frames = duration * fps
        all_frames = []          # 每帧图像（长度 == total_frames）
        defect_labels = []       # [{frame_index, bbox_x, ...}]
        defects = []             # 缺陷轨迹配置

        road_left, road_right = width // 4, width * 3 // 4

        def add_defects(label, shape, base_kwargs):
            """为某类缺陷随机生成 2~10 条轨迹"""
            cnt = np.random.randint(2, 11)
            for _ in range(cnt):
                start_t = float(np.random.uniform(0, max(0.1, duration - 1)))
                end_t   = float(min(duration, start_t + np.random.uniform(0.5, 1.5)))
                x_pos   = int(np.random.randint(road_left + 50, road_right - 50))
                defects.append(
                    dict(label=label, shape=shape, start=start_t, end=end_t,
                         x=x_pos, start_y=height + 150, end_y=-150, **base_kwargs)
                )

        add_defects("裂缝", "line",   {"length": 300, "thickness": 8, "color": (30, 30, 30)})
        add_defects("坑槽", "circle", {"size": 120, "color": (80, 80, 80)})

        with imageio.get_writer(str(path),
                                fps=fps,
                                codec="libx264",
                                bitrate="2M",
                                macro_block_size=None) as writer:
            for t in range(total_frames):
                img = np.full((height, width, 3), (34, 139, 34), np.uint8)

                # 画公路背景
                img[:, road_left:road_right] = (50, 50, 50)
                offset = (t * 20) % 80
                for y in range(-offset, height, 80):
                    img[y:y+40, width//2-5:width//2+5] = (255, 255, 255)

                time_sec = t / fps
                for idx, df in enumerate(defects):
                    if not (df["start"] <= time_sec <= df["end"]):
                        continue
                    ratio = (time_sec - df["start"]) / (df["end"] - df["start"])
                    cx    = int(df["x"])
                    cy    = int(df["start_y"] + ratio * (df["end_y"] - df["start_y"]))
                    shape = df["shape"]

                    # ---------- 根据形状画缺陷并计算 bbox ----------
                    if shape == "circle":
                        r = df["size"] // 2
                        cv2.circle(img, (cx, cy), r, df["color"], -1)
                        x, y, w, h = cx - r, cy - r, 2*r, 2*r
                    elif shape == "line":
                        L       = df["length"]
                        thick   = df["thickness"]
                        segments = 8
                        amp      = thick * 2
                        pts = [
                            (int(cx + ((-1) ** i) * amp),
                             int(cy - L/2 + i * L / (segments - 1)))
                            for i in range(segments)
                        ]
                        cv2.polylines(img, [np.array(pts, dtype=np.int32)],
                                      False, df["color"], thick)
                        x, y, w, h = cv2.boundingRect(np.array(pts, dtype=np.int32))
                        # 扩一点边缘
                        pad = thick
                        x, y, w, h = x-pad, y-pad, w+2*pad, h+2*pad
                    else:
                        continue

                    # 裁剪到画面边界
                    x = max(0, x);    y = max(0, y)
                    w = min(w, width  - x)
                    h = min(h, height - y)

                    defect_labels.append(
                        dict(frame_index=t,
                             time=round(time_sec, 3),
                             bbox_x=x / width,
                             bbox_y=y / height,
                             bbox_width=w / width,
                             bbox_height=h / height,
                             label=df["label"],
                             track_id=idx)  # 轨迹编号 == defects 列表索引
                    )

                # 保存帧
                all_frames.append(img.copy())
                writer.append_data(img)

        return all_frames, defect_labels, fps

    # ---------- 2. 主入口 ----------
    def handle(self, *args, **options):
        # 清空旧数据
        for model in reversed(list(apps.get_app_config("web").get_models())):
            if model._meta.db_table in connection.introspection.table_names():
                model.objects.all().delete()

        # 重建 media/demo
        media_root = Path("media")
        shutil.rmtree(media_root, ignore_errors=True)
        base_dir = media_root / "demo"
        base_dir.mkdir(parents=True, exist_ok=True)
        video_path = base_dir / "demo_video.mp4"

        # 生成视频 + 标签
        duration = 10
        all_frames, defect_labels, fps = self._generate_demo_video_with_defects(
            video_path, duration=duration, fps=30
        )
        total_frames = duration * fps

        # ---------- 3. 业务表准备 ----------
        severity, _    = SeverityLevel.objects.get_or_create(name="轻度", code="low")
        report_type, _ = ReportType.objects.get_or_create(name="日常报表", code="daily")
        mtype, _       = MediaType.objects.get_or_create(name="图片", code="image")

        weather_opts = [("晴天", "sunny", 26),
                        ("多云", "cloudy", 24),
                        ("小雨", "rain", 22),
                        ("阴天", "overcast", 23),
                        ("大风", "windy", 28)]
        weather_list = [WeatherType.objects.get_or_create(name=n, code=c)[0]
                        for n, c, _ in weather_opts]

        # 将 frame label 按轨迹分组
        labels_by_track = {}
        for lab in defect_labels:
            labels_by_track.setdefault(lab["track_id"], []).append(lab)
        track_groups = list(labels_by_track.values())   # 每元素 = 同一轨迹所有帧标签

        days = getattr(settings, "DEMO_DAYS", 5)
        for day in range(days):
            ts       = timezone.now() - timedelta(days=day)
            weather  = weather_list[day % len(weather_list)]
            temp     = weather_opts[day % len(weather_opts)][2]

            batch = DetectionBatch.objects.create(
                start_time=ts,
                end_time=ts,
                airport=f"A{day+1}",
                drone_id=f"D{day+1}",
                weather=weather,
                temperature=temp,
                video_link=f"{settings.MEDIA_URL}demo/demo_video.mp4",
                total_frames=total_frames,
                video_duration=duration,
            )
            report = Report.objects.create(batch=batch, report_type=report_type)

            # *** 关键修正：每天导入「全部」轨迹，保证数据与视频一致 ***
            for idx, items in enumerate(track_groups, 1):
                items.sort(key=lambda x: x["frame_index"])
                label  = items[0]["label"]
                d_type, _ = DiseaseType.objects.get_or_create(name=label)

                track = DefectTrack.objects.create(
                    batch=batch,
                    disease_type=d_type,
                    unique_code=f"DEMO-{day+1}-{idx}",
                    severity=severity,
                    start_frame=items[0]["frame_index"],
                    end_frame=items[-1]["frame_index"],
                    start_time=items[0]["time"],
                    end_time=items[-1]["time"],
                    report=report,
                )

                # 保存帧图片 + GT
                for lab in items:
                    frame_img  = all_frames[lab["frame_index"]]
                    frame_name = f"day{day}_{label}_{lab['frame_index']}.jpg"
                    frame_path = base_dir / frame_name
                    imageio.imwrite(str(frame_path), frame_img)

                    DiseaseMedia.objects.create(
                        defect_track=track,
                        media_type=mtype,
                        file_link=f"{settings.MEDIA_URL}demo/{frame_name}",
                    )
                    GroundTruthFrame.objects.create(
                        track=track,
                        frame_index=lab["frame_index"],
                        time=lab["time"],
                        bbox_x=lab["bbox_x"],
                        bbox_y=lab["bbox_y"],
                        bbox_width=lab["bbox_width"],
                        bbox_height=lab["bbox_height"],
                    )

        self.stdout.write(self.style.SUCCESS("✅  Demo video, images, and GT labels generated!"))
