from django.test import TestCase
from django.urls import reverse

from .models import (
    DetectionBatch,
    DefectTrack,
    DiseaseType,
    GroundTruthFrame,
    WeatherType,
    MediaType,
    DiseaseMedia,
)


class AnomalyBoxesAPITest(TestCase):
    def setUp(self):
        dtype = DiseaseType.objects.create(name="裂缝")
        weather = WeatherType.objects.create(name="晴天", code="sunny")
        batch = DetectionBatch.objects.create(
            start_time="2024-01-01T00:00:00Z",
            end_time="2024-01-01T01:00:00Z",
            airport="A1",
            drone_id="D1",
            weather=weather,
            video_link="/media/demo.mp4",
        )
        track = DefectTrack.objects.create(
            batch=batch,
            disease_type=dtype,
            unique_code="TRK1",
            start_frame=10,
            end_frame=12,
        )
        GroundTruthFrame.objects.create(
            track=track,
            frame_index=10,
            time=0.4,
            bbox_x=0.1,
            bbox_y=0.2,
            bbox_width=0.3,
            bbox_height=0.4,
        )
        GroundTruthFrame.objects.create(
            track=track,
            frame_index=11,
            time=0.5,
            bbox_x=0.15,
            bbox_y=0.25,
            bbox_width=0.3,
            bbox_height=0.4,
        )

    def test_boxes_api(self):
        resp = self.client.get(reverse("anomaly_boxes"))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data["frames"]), 2)
        first_box = data["frames"][0]["boxes"][0]
        self.assertEqual(first_box["start"], 10)
        self.assertEqual(first_box["end"], 12)
        self.assertEqual(first_box["label"], "裂缝")


class DashboardStatsAPITest(TestCase):
    def setUp(self):
        dtype = DiseaseType.objects.create(name="裂缝")
        weather = WeatherType.objects.create(name="晴天", code="sunny")
        self.batch = DetectionBatch.objects.create(
            start_time="2024-01-01T00:00:00Z",
            end_time="2024-01-01T01:00:00Z",
            airport="A1",
            drone_id="D1",
            weather=weather,
        )
        DefectTrack.objects.create(
            batch=self.batch,
            disease_type=dtype,
            unique_code="REC1",
            start_frame=1,
            end_frame=2,
            develop_trend="已修复",
        )
        DefectTrack.objects.create(
            batch=self.batch,
            disease_type=dtype,
            unique_code="REC2",
            start_frame=3,
            end_frame=4,
            develop_trend="扩大",
        )

    def test_stats(self):
        resp = self.client.get(reverse("stats"))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["inspection_count"], 1)
        self.assertEqual(data["pending_count"], 1)
        self.assertAlmostEqual(data["completion_rate"], 50.0)

    def test_stats_with_batch(self):
        resp = self.client.get(reverse("stats"), {"batch": self.batch.id})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("batch", data)
        self.assertEqual(data["batch"]["defect_count"], 2)
        self.assertEqual(data["batch"]["pending_count"], 1)
        self.assertAlmostEqual(data["batch"]["completion_rate"], 50.0)


class DefectTracksAPITest(TestCase):
    def setUp(self):
        dtype = DiseaseType.objects.create(name="裂缝")
        weather = WeatherType.objects.create(name="晴天", code="sunny")
        mtype = MediaType.objects.create(name="图片", code="image")
        batch = DetectionBatch.objects.create(
            start_time="2024-01-01T00:00:00Z",
            end_time="2024-01-01T01:00:00Z",
            airport="A1",
            drone_id="D1",
            weather=weather,
            video_link="/media/demo.mp4",
        )
        track = DefectTrack.objects.create(
            batch=batch,
            disease_type=dtype,
            unique_code="REC1",
            start_frame=1,
            end_frame=2,
            start_time=0.0,
        )
        DiseaseMedia.objects.create(
            defect_track=track,
            media_type=mtype,
            file_link="/media/frame1.jpg",
        )

    def test_defect_tracks(self):
        resp = self.client.get(reverse("defect_tracks"))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data["tracks"]), 1)
        self.assertEqual(data["tracks"][0]["start"], 0.0)
        self.assertIn("/media/frame1.jpg", data["tracks"][0]["snapshot"])


class DiseaseTypeStatsAPITest(TestCase):
    def setUp(self):
        dtype1 = DiseaseType.objects.create(name="裂缝")
        dtype2 = DiseaseType.objects.create(name="坑槽")
        weather = WeatherType.objects.create(name="晴天", code="sunny")
        batch = DetectionBatch.objects.create(
            start_time="2024-01-01T00:00:00Z",
            end_time="2024-01-01T01:00:00Z",
            airport="A1",
            drone_id="D1",
            weather=weather,
        )
        DefectTrack.objects.create(
            batch=batch,
            disease_type=dtype1,
            unique_code="D1",
            start_frame=1,
            end_frame=2,
        )
        DefectTrack.objects.create(
            batch=batch,
            disease_type=dtype2,
            unique_code="D2",
            start_frame=1,
            end_frame=2,
        )
        DefectTrack.objects.create(
            batch=batch,
            disease_type=dtype2,
            unique_code="D3",
            start_frame=1,
            end_frame=2,
        )

    def test_disease_type_stats(self):
        resp = self.client.get(reverse("disease_type_stats"))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        label_data = dict(zip(data["labels"], data["data"]))
        self.assertEqual(label_data["裂缝"], 1)
        self.assertEqual(label_data["坑槽"], 2)


class DetectionBatchesAPITest(TestCase):
    def setUp(self):
        weather = WeatherType.objects.create(name="晴天", code="sunny")
        self.batch1 = DetectionBatch.objects.create(
            start_time="2024-01-01T00:00:00Z",
            end_time="2024-01-01T01:00:00Z",
            airport="A1",
            drone_id="D1",
            weather=weather,
        )
        self.batch2 = DetectionBatch.objects.create(
            start_time="2024-01-02T00:00:00Z",
            end_time="2024-01-02T01:00:00Z",
            airport="A2",
            drone_id="D2",
            weather=weather,
        )

    def test_detection_batches(self):
        resp = self.client.get(reverse("batches"))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        ids = [b["id"] for b in data["batches"]]
        self.assertCountEqual(ids, [self.batch1.id, self.batch2.id])
