"""小程序专属的 token 签发与校验。

复用项目已安装的 ``djangorestframework-simplejwt``，但走独立的 token 通道：
token 载荷携带 ``openid``，有效期 7 天，不与网站后台的 Django User 体系混用。
"""
from datetime import timedelta

from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed, InvalidToken
from rest_framework_simplejwt.tokens import AccessToken

from .models import WeChatUser

#: token 有效期，文档要求 7 天且不设 refresh token。
TOKEN_LIFETIME = timedelta(days=getattr(settings, 'CHECKIN_TOKEN_LIFETIME_DAYS', 7))


def issue_token(openid):
    """为指定 openid 签发一个 7 天有效期的 access token。

    Args:
        openid (str): 微信用户唯一标识。

    Returns:
        tuple[str, int]: ``(token 字符串, 过期时间戳)``，过期时间为 Unix 秒。
    """
    token = AccessToken()          # 无参构造：token_type 为 'access'，可被默认校验识别
    token['openid'] = openid
    token.set_exp(lifetime=TOKEN_LIFETIME)
    return str(token), int(token['exp'])   # exp 为 Unix 秒


class WeChatJWTAuthentication(JWTAuthentication):
    """基于 ``openid`` claim 的自定义鉴权类。

    仅重写 ``get_user``：从 token 的 ``openid`` 反查 ``WeChatUser``，
    因此不会与网站默认 ``JWTAuthentication``（读取 ``user_id`` claim）互相干扰。
    """

    def get_user(self, validated_token):
        """根据 token 中的 openid 取出对应的微信用户。

        Args:
            validated_token (Token): 已通过签名与有效期校验的 token。

        Returns:
            WeChatUser: 对应的微信用户实例。

        Raises:
            InvalidToken: token 中缺少 openid。
            AuthenticationFailed: openid 对应的用户不存在。
        """
        openid = validated_token.get('openid')
        if not openid:
            raise InvalidToken('Token 缺少 openid')
        try:
            return WeChatUser.objects.get(pk=openid)
        except WeChatUser.DoesNotExist as exc:
            raise AuthenticationFailed('User not found', code='user_not_found') from exc
