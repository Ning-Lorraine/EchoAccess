from django.shortcuts import render, redirect
from .models import Video
from .forms import VideoForm

# def videoplayer(request):
#     if request.method == 'POST':
#         form = VideoForm(request.POST, request.FILES)
#         if form.is_valid():
#             form.save()
#             # video = form.save()
#             # video.save()
#             # # 生成并保存缩略图
#             # thumbnail_path = generate_thumbnail(video.video_file.path,video.video_file.name)
#             # video.thumbnail = thumbnail_path
#             # video.save()
#             return redirect('videoplayer')
#     else:
#         form = VideoForm()
    
#     videos = Video.objects.all()
#     return render(request, 'video/videoplayer.html', {'form': form, 'videos': videos})

def videoplayer(request):
    if request.method == 'POST':
        form = VideoForm(request.POST, request.FILES)  # 包含 request.FILES
        if form.is_valid():
            form.save()
            return redirect('videoplayer')
        else:
            print(form.errors)  # 打印表单验证失败的错误信息
    else:
        form = VideoForm()
    
    videos = Video.objects.all()
    return render(request, 'video/videoplayer.html', {'form': form, 'videos': videos})


