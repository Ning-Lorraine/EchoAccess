from django.urls import path
from . import views

urlpatterns = [
    # path('videos/', views.video_list, name='video_list'),
    # path('upload/', views.upload_video, name='upload_video'),
    path('player/', views.videoplayer, name='videoplayer'),
    path('', views.index, name='index'),
]
     