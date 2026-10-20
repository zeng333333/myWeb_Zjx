from django.urls import path, include

urlpatterns = [
    path('auth/', include('hub.auth_urls')),
    path('store/', include('store.api.urls')),
    path('checkin/', include('checkin.urls')),
]
