from django.db import models

class DiseaseType(models.Model):
    """病害类型，如裂缝、坑槽等"""
    name = models.CharField("病害名称", max_length=64, unique=True)
    description = models.TextField("病害描述", blank=True)
    class Meta:
        db_table = "disease_type"
        verbose_name = "病害类型"
        verbose_name_plural = "病害类型"
    def __str__(self):
        return self.name

class WeatherType(models.Model):
    """天气类型，可扩展"""
    name = models.CharField("天气名称", max_length=16, unique=True)  # 晴天/阴天/小雨/小雪
    code = models.CharField("代码", max_length=16, unique=True, help_text="英文或拼音等唯一标识")
    class Meta:
        db_table = "weather_type"
        verbose_name = "天气类型"
        verbose_name_plural = "天气类型"
    def __str__(self):
        return self.name

class SeverityLevel(models.Model):
    """病害严重程度"""
    name = models.CharField("严重等级", max_length=32, unique=True)  # 轻/中/重/致命
    code = models.CharField("代码", max_length=16, unique=True)
    description = models.CharField("说明", max_length=128, blank=True)
    class Meta:
        db_table = "severity_level"
        verbose_name = "严重程度"
        verbose_name_plural = "严重程度"
    def __str__(self):
        return self.name

class ReportType(models.Model):
    """报表类型"""
    name = models.CharField("报表名称", max_length=32, unique=True)
    code = models.CharField("代码", max_length=16, unique=True)
    description = models.CharField("说明", max_length=128, blank=True)
    class Meta:
        db_table = "report_type"
        verbose_name = "报表类型"
        verbose_name_plural = "报表类型"
    def __str__(self):
        return self.name

class MediaType(models.Model):
    """媒体类型（图片、视频等）"""
    name = models.CharField("类型名称", max_length=16, unique=True)
    code = models.CharField("代码", max_length=16, unique=True)
    class Meta:
        db_table = "media_type"
        verbose_name = "媒体类型"
        verbose_name_plural = "媒体类型"
    def __str__(self):
        return self.name

class DetectionBatch(models.Model):
    """无人机检测批次，含起降机场、天气等"""
    start_time = models.DateTimeField("起飞时间")
    end_time = models.DateTimeField("降落时间")
    airport = models.CharField("起降机场", max_length=32)
    drone_id = models.CharField("无人机编号", max_length=32)
    weather = models.ForeignKey(
        WeatherType, on_delete=models.SET_NULL, null=True, verbose_name="天气"
    )
    temperature = models.FloatField("温度(℃)", null=True, blank=True)
    status = models.CharField(
        "批次状态",
        max_length=16,
        default="done",
        help_text="如 done/processing/failed，后续可扩展独立状态表"
    )
    video_link = models.URLField("视频链接", blank=True)
    flight_duration = models.FloatField("飞行时长(分钟)", null=True, blank=True)
    recharge_time = models.FloatField("充电时长(分钟)", null=True, blank=True)
    total_frames = models.PositiveIntegerField("采集帧数", null=True, blank=True)
    video_duration = models.FloatField("视频时长(秒)", null=True, blank=True)
    is_archived = models.BooleanField("已归档", default=False)
    expire_at = models.DateTimeField("到期时间", null=True, blank=True)
    class Meta:
        db_table = "detection_batch"
        verbose_name = "检测批次"
        verbose_name_plural = "检测批次"
        ordering = ["-start_time"]
    def __str__(self):
        return f"{self.airport}-{self.start_time:%Y%m%d%H%M}"

class Report(models.Model):
    """病害检测报表"""
    batch = models.ForeignKey(DetectionBatch, on_delete=models.CASCADE, verbose_name="检测批次")
    report_type = models.ForeignKey(ReportType, on_delete=models.SET_NULL, null=True, verbose_name="报表类型")
    generated_at = models.DateTimeField("生成时间", auto_now_add=True)
    file_link = models.URLField("报表文件链接", blank=True)
    content = models.TextField("报表内容简要", blank=True)
    class Meta:
        db_table = "report"
        verbose_name = "检测报表"
        verbose_name_plural = "检测报表"
    def __str__(self):
        return f"{self.batch} - {self.report_type or ''}"

class DefectTrack(models.Model):
    """同一缺陷在视频中的跟踪记录"""
    batch = models.ForeignKey(
        DetectionBatch, on_delete=models.CASCADE, verbose_name="检测批次"
    )
    disease_type = models.ForeignKey(
        DiseaseType, on_delete=models.PROTECT, verbose_name="病害类型"
    )
    unique_code = models.CharField("病害编号", max_length=64, unique=True)
    severity = models.ForeignKey(
        SeverityLevel, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="严重程度"
    )
    start_frame = models.PositiveIntegerField("起始帧")
    end_frame = models.PositiveIntegerField("结束帧")
    start_time = models.FloatField("起始时间(秒)", null=True, blank=True)
    end_time = models.FloatField("结束时间(秒)", null=True, blank=True)
    develop_trend = models.CharField(
        "发展趋势", max_length=32, blank=True, help_text="如扩大/无变化/已修复"
    )
    snapshot_link = models.URLField("病害截图链接", blank=True)
    report = models.ForeignKey(
        Report, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="关联报表"
    )
    class Meta:
        db_table = "defect_track"
        verbose_name = "缺陷轨迹"
        verbose_name_plural = "缺陷轨迹"
    def __str__(self):
        return self.unique_code

class DiseaseMedia(models.Model):
    """病害相关媒体（截图、视频、报告附件等）"""
    defect_track = models.ForeignKey(DefectTrack, on_delete=models.CASCADE, related_name="media", verbose_name="病害轨迹")
    media_type = models.ForeignKey(MediaType, on_delete=models.PROTECT, verbose_name="媒体类型")
    file_link = models.URLField("文件链接")
    description = models.CharField("描述", max_length=128, blank=True)
    class Meta:
        db_table = "disease_media"
        verbose_name = "病害媒体"
        verbose_name_plural = "病害媒体"
    def __str__(self):
        return f"{self.defect_track} - {self.media_type.name}"

class GroundTruthFrame(models.Model):
    """缺陷在某一视频帧上的标注信息"""
    track = models.ForeignKey(
        DefectTrack,
        on_delete=models.CASCADE,
        related_name="frames",
        verbose_name="缺陷轨迹",
    )
    frame_index = models.PositiveIntegerField("帧序号")
    time = models.FloatField("时间(秒)", null=True, blank=True)
    bbox_x = models.FloatField("框左上角X", help_text="归一化坐标0-1")
    bbox_y = models.FloatField("框左上角Y", help_text="归一化坐标0-1")
    bbox_width = models.FloatField("框宽度", help_text="归一化比例0-1")
    bbox_height = models.FloatField("框高度", help_text="归一化比例0-1")
    class Meta:
        db_table = "ground_truth_frame"
        verbose_name = "缺陷帧标注"
        verbose_name_plural = "缺陷帧标注"
        ordering = ["frame_index"]
    def __str__(self):
        return f"{self.track}-{self.frame_index}"
