"""微信开放接口调用封装（服务端对服务端）。

仅使用标准库 ``urllib``，不引入额外的 HTTP 依赖。
"""
import json
import urllib.parse
import urllib.request

from django.conf import settings


class WeChatAPIError(Exception):
    """调用微信接口失败（网络异常、超时或返回体无法解析）。"""


def jscode2session(code, timeout=5):
    """用 ``wx.login()`` 拿到的 code 换取 openid。

    Args:
        code (str): 小程序端 ``wx.login()`` 返回的一次性 code（5 分钟有效）。
        timeout (int): 请求微信接口的超时秒数，默认 5 秒。

    Returns:
        dict: 微信返回的原始字典。成功时包含 ``openid`` / ``session_key``；
        失败时包含 ``errcode`` / ``errmsg``。

    Raises:
        WeChatAPIError: 网络超时、连接失败或返回体不是合法 JSON。
    """
    params = urllib.parse.urlencode({
        'appid': settings.WECHAT_APPID,
        'secret': settings.WECHAT_SECRET,
        'js_code': code,
        'grant_type': 'authorization_code',
    })
    url = 'https://api.weixin.qq.com/sns/jscode2session?' + params
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            raw = resp.read().decode('utf-8')
    except Exception as exc:  # 网络类异常统一收敛
        raise WeChatAPIError(str(exc)) from exc
    try:
        return json.loads(raw)
    except ValueError as exc:
        raise WeChatAPIError('invalid upstream response') from exc
