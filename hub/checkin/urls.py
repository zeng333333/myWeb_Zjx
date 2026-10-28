from django.urls import path

from . import views

urlpatterns = [
    path('login/', views.WeChatLoginView.as_view(), name='checkin_login'),
    path('sync/pull/', views.SyncPullView.as_view(), name='checkin_sync_pull'),
    path('sync/push/', views.SyncPushView.as_view(), name='checkin_sync_push'),
    path('space/', views.SpaceInfoView.as_view(), name='checkin_space_info'),
    path('space/code/', views.SpaceCodeCreateView.as_view(), name='checkin_space_code'),
    path('space/join/', views.SpaceJoinView.as_view(), name='checkin_space_join'),
    path('space/leave/', views.SpaceLeaveView.as_view(), name='checkin_space_leave'),
]
