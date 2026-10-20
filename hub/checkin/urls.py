from django.urls import path

from . import views

urlpatterns = [
    path('login/', views.WeChatLoginView.as_view(), name='checkin_login'),
    path('sync/pull/', views.SyncPullView.as_view(), name='checkin_sync_pull'),
    path('sync/push/', views.SyncPushView.as_view(), name='checkin_sync_push'),
]
