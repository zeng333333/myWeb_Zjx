from django.contrib import admin

from .models import SyncSnapshot, WeChatUser


@admin.register(WeChatUser)
class WeChatUserAdmin(admin.ModelAdmin):
    """微信用户只读后台，便于排查同步问题。"""

    list_display = ('openid', 'created_at', 'last_seen')
    search_fields = ('openid',)
    readonly_fields = ('openid', 'created_at', 'last_seen')


@admin.register(SyncSnapshot)
class SyncSnapshotAdmin(admin.ModelAdmin):
    """数据快照只读后台，payload 不解析、原样展示。"""

    list_display = ('openid', 'version', 'updated_at')
    search_fields = ('openid',)
    readonly_fields = ('openid', 'version', 'payload', 'updated_at')
