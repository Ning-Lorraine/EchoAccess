from django.db import models
# import uuid

# def file_upload_to(instance, filename):
#     ext = filename.split('.')[-1]
#     # 生成UUID文件名
#     filename = f"{uuid.uuid4()}.{ext}"
#     return f"videos/{filename}"

class Video(models.Model):
    title = models.CharField(max_length=255)
    video_file = models.FileField(upload_to='videos/')
    # thumbnail = models.ImageField(upload_to='thumbnails/', null=True, blank=True)
