from django.db import models


class WeChatUser(models.Model):
    """微信小程序用户，以 openid 作为唯一标识。

    该表只服务于打卡小程序的云同步，与网站后台的 Django User 完全隔离。
    openid 直接作为主键，便于自定义鉴权按 openid 反查。
    """

    openid = models.CharField(max_length=64, primary_key=True, verbose_name='openid')
    created_at = models.BigIntegerField(verbose_name='创建时间(毫秒)')
    last_seen = models.BigIntegerField(verbose_name='最近活跃(毫秒)')

    @property
    def is_authenticated(self):
        """DRF 要求 request.user 必须具备该属性，恒为 True。"""
        return True

    @property
    def is_anonymous(self):
        """DRF 要求 request.user 必须具备该属性，恒为 False。"""
        return False

    def __str__(self):
        return self.openid

    class Meta:
        verbose_name = '微信用户'
        verbose_name_plural = '微信用户'


class SyncSnapshot(models.Model):
    """用户数据的整包快照，服务端不解析 payload 内部字段。

    payload 原样存 JSON 字符串；``payload is None`` 表示云端还没有任何数据。
    version 从 0 开始，0 表示「还没有任何数据」，成功 push 后单调递增。
    """

    openid = models.CharField(max_length=64, primary_key=True, verbose_name='openid')
    version = models.IntegerField(default=0, verbose_name='版本号')
    payload = models.TextField(null=True, blank=True, verbose_name='数据快照(JSON)')
    updated_at = models.BigIntegerField(null=True, blank=True, verbose_name='更新时间(毫秒)')

    def __str__(self):
        return f'{self.openid} v{self.version}'

    class Meta:
        verbose_name = '数据快照'
        verbose_name_plural = '数据快照'
