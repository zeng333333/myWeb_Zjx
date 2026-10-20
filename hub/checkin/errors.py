"""统一 checkin 接口的错误响应格式 ``{ "error": "<机器码>", "message": "<中文>" }``。

DRF 默认错误体是 ``{"detail": "..."}``，与交接文档约定不符，这里只在
checkin 视图内做重映射，不影响网站其他接口。
"""
from rest_framework.response import Response
from rest_framework.views import exception_handler

#: HTTP 状态码 -> (机器码, 默认中文说明)
_ERROR_MAP = {
    400: ('invalid_payload', '请求参数不合法'),
    401: ('unauthorized', '未授权或登录已过期'),
    405: ('invalid_payload', '请求方法不被允许'),
    413: ('payload_too_large', '请求体过大'),
    429: ('rate_limited', '请求过于频繁'),
    500: ('server_error', '服务端异常'),
}


def error_response(error, message, status_code, **extra):
    """构造符合交接文档约定的错误响应。

    Args:
        error (str): 机器可读的错误码，如 ``invalid_payload``。
        message (str): 面向用户的中文说明。
        status_code (int): HTTP 状态码。
        **extra: 需要一并返回的附加字段（如 409 冲突时的 version/payload）。

    Returns:
        Response: DRF 响应对象。
    """
    body = {'error': error, 'message': message}
    body.update(extra)
    return Response(body, status=status_code)


def checkin_exception_handler(exc, context):
    """checkin 视图专属异常处理器，把 DRF 默认错误体转为统一格式。

    Args:
        exc (Exception): DRF 抛出的异常。
        context (dict): 异常上下文。

    Returns:
        Response | None: 转换后的响应；无法处理时返回 None。
    """
    response = exception_handler(exc, context)
    if response is None:
        return None
    code, default_message = _ERROR_MAP.get(response.status_code, ('server_error', '服务端异常'))
    detail = response.data
    message = default_message
    if isinstance(detail, dict):
        message = detail.get('detail') or detail.get('message') or default_message
    return Response({'error': code, 'message': str(message)}, status=response.status_code)
