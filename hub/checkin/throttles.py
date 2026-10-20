"""checkin 接口限流：每 openid 每分钟 60 次、每 IP 每分钟 300 次。

注意：项目未配置共享缓存，DRF 默认使用进程内 ``LocMemCache``，在 Gunicorn
多 worker 下实际阈值约为配置值的 worker 倍数。若需精确限流，应改用 Redis
或在 ``settings.py`` 配置 DB 后端缓存。
"""
from rest_framework.throttling import SimpleRateThrottle


class OpenidRateThrottle(SimpleRateThrottle):
    """按 openid 维度限流，每 openid 每分钟 60 次。"""

    scope = 'checkin_openid'
    rate = '60/min'

    def get_cache_key(self, request, view):
        """以 openid 作为限流键。

        Args:
            request (Request): 当前请求。
            view (APIView): 当前视图。

        Returns:
            str | None: 限流键；无 openid（如登录接口）时返回 None，表示不限流。
        """
        openid = getattr(request.user, 'openid', None)
        if not openid:
            return None
        return self.cache_format % {'scope': self.scope, 'ident': openid}


class IPRateThrottle(SimpleRateThrottle):
    """按来源 IP 维度限流，每 IP 每分钟 300 次。"""

    scope = 'checkin_ip'
    rate = '300/min'

    def get_cache_key(self, request, view):
        """以客户端来源 IP 作为限流键。

        Args:
            request (Request): 当前请求。
            view (APIView): 当前视图。

        Returns:
            str: 限流键。
        """
        return self.cache_format % {'scope': self.scope, 'ident': self.get_ident(request)}
