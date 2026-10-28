import secrets

from django.db import models


def _new_space_id():
    """生成空间 ID。

    Returns:
        str: ``sp_`` 前缀加 16 位十六进制随机串，如 ``sp_9f2c4a1b3e8d07c5``。
    """
    return f'sp_{secrets.token_hex(8)}'


def _new_bind_code():
    """生成 6 位数字绑定码。

    Returns:
        str: 6 位数字字符串，使用 ``secrets`` 保证不可预测。
    """
    return f'{secrets.randbelow(900000) + 100000}'


class Space(models.Model):
    """数据空间：一份快照的归属单位，可包含多个微信号。"""

    id = models.CharField(max_length=40, primary_key=True, default=_new_space_id, verbose_name='空间ID')
    owner_openid = models.CharField(max_length=64, verbose_name='创建者openid')
    created_at = models.BigIntegerField(verbose_name='创建时间(毫秒)')

    def __str__(self):
        return self.id

    class Meta:
        verbose_name = '数据空间'
        verbose_name_plural = '数据空间'


class WeChatUser(models.Model):
    """微信小程序用户，以 openid 作为唯一标识。

    该表只服务于打卡小程序的云同步，与网站后台的 Django User 完全隔离。
    openid 直接作为主键，便于自定义鉴权按 openid 反查。
    ``space`` 指向其当前所在的数据空间，登录时自动创建单人空间兜底。
    """

    openid = models.CharField(max_length=64, primary_key=True, verbose_name='openid')
    space = models.ForeignKey(Space, null=True, on_delete=models.SET_NULL,
                              related_name='members', verbose_name='所属空间')
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


class SpaceCode(models.Model):
    """一次性空间绑定码：6 位数字，10 分钟有效，用一次即作废。"""

    code = models.CharField(max_length=6, primary_key=True, default=_new_bind_code, verbose_name='绑定码')
    space = models.ForeignKey(Space, on_delete=models.CASCADE, related_name='codes', verbose_name='目标空间')
    expire_at = models.BigIntegerField(verbose_name='过期时间(Unix秒)')
    used_at = models.BigIntegerField(null=True, blank=True, verbose_name='使用时间(Unix秒)')

    def __str__(self):
        return self.code

    class Meta:
        verbose_name = '空间绑定码'
        verbose_name_plural = '空间绑定码'


class SyncSnapshot(models.Model):
    """空间数据的整包快照，服务端不解析 payload 内部字段。

    payload 原样存 JSON 字符串；``payload is None`` 表示云端还没有任何数据。
    version 从 0 开始，0 表示「还没有任何数据」，成功 push 后单调递增。
    同一空间内的所有成员读写同一份快照。
    """

    space = models.OneToOneField(Space, primary_key=True, on_delete=models.CASCADE,
                                 related_name='snapshot', verbose_name='所属空间')
    version = models.IntegerField(default=0, verbose_name='版本号')
    payload = models.TextField(null=True, blank=True, verbose_name='数据快照(JSON)')
    updated_at = models.BigIntegerField(null=True, blank=True, verbose_name='更新时间(毫秒)')

    def __str__(self):
        return f'{self.space_id} v{self.version}'

    class Meta:
        verbose_name = '数据快照'
        verbose_name_plural = '数据快照'
