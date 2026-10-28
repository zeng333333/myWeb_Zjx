from django.contrib import admin

from .models import Space, SpaceCode, SyncSnapshot, WeChatUser


@admin.register(Space)
class SpaceAdmin(admin.ModelAdmin):
    """数据空间只读后台。"""

    list_display = ('id', 'owner_openid', 'created_at')
    search_fields = ('id', 'owner_openid')
    readonly_fields = ('id', 'owner_openid', 'created_at')


@admin.register(WeChatUser)
class WeChatUserAdmin(admin.ModelAdmin):
    """微信用户只读后台，便于排查同步问题。"""

    list_display = ('openid', 'space', 'created_at', 'last_seen')
    search_fields = ('openid',)
    readonly_fields = ('openid', 'space', 'created_at', 'last_seen')


@admin.register(SpaceCode)
class SpaceCodeAdmin(admin.ModelAdmin):
    """空间绑定码只读后台。"""

    list_display = ('code', 'space', 'expire_at', 'used_at')
    search_fields = ('code', 'space_id')
    readonly_fields = ('code', 'space', 'expire_at', 'used_at')


@admin.register(SyncSnapshot)
class SyncSnapshotAdmin(admin.ModelAdmin):
    """数据快照只读后台，payload 不解析、原样展示。"""

    list_display = ('space', 'version', 'updated_at')
    search_fields = ('space_id',)
    readonly_fields = ('space', 'version', 'payload', 'updated_at')
