"""checkin 云同步接口：login / sync.pull / sync.push。"""
import json
import logging
import time

from django.conf import settings
from django.db import transaction
from django.db.models import F
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .authentication import WeChatJWTAuthentication, issue_token
from .errors import checkin_exception_handler, error_response
from .models import SyncSnapshot, WeChatUser
from .serializers import LoginSerializer, PushSerializer
from .throttles import IPRateThrottle, OpenidRateThrottle
from .wechat import WeChatAPIError, jscode2session

logger = logging.getLogger('checkin')


def _now_ms():
    """返回当前毫秒时间戳。

    Returns:
        int: 与 ``Date.now()`` 对齐的毫秒时间戳。
    """
    return int(time.time() * 1000)


def _content_length(request):
    """读取请求体声明的字节长度。

    Args:
        request (Request): DRF 请求对象。

    Returns:
        int: CONTENT_LENGTH 声明的字节数；缺失或非法时返回 0。
    """
    try:
        return int(request.META.get('CONTENT_LENGTH') or 0)
    except (TypeError, ValueError):
        return 0


class CheckinAPIView(APIView):
    """checkin 接口基类，统一挂载专属异常处理器以保证错误格式一致。"""

    def get_exception_handler(self):
        """返回 checkin 专属异常处理器。

        Returns:
            callable: ``checkin_exception_handler``。
        """
        return checkin_exception_handler


class WeChatLoginView(CheckinAPIView):
    """``POST /api/checkin/login/``：code 换 openid 并签发 token。"""

    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = [IPRateThrottle]

    def post(self, request):
        """处理登录请求。

        Args:
            request (Request): 含 ``code`` 的请求。

        Returns:
            Response: 成功返回 ``{token, expireAt}``；失败返回统一错误体。
        """
        logger.info('login 收到的请求体: %s', json.dumps(request.data, ensure_ascii=False, default=str))
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response('invalid_code', 'code 不能为空', status.HTTP_400_BAD_REQUEST)
        code = serializer.validated_data['code']
        logger.info('login 实际发给微信的 js_code: %r', code)

        try:
            data = jscode2session(code)
        except WeChatAPIError:
            return error_response('upstream_error', '调用微信接口失败', status.HTTP_502_BAD_GATEWAY)

        if data.get('errcode') or not data.get('openid'):
            return error_response('code_rejected', 'code 无效或已被使用', status.HTTP_401_UNAUTHORIZED)

        openid = data['openid']
        now = _now_ms()
        _, created = WeChatUser.objects.get_or_create(
            openid=openid,
            defaults={'created_at': now, 'last_seen': now},
        )
        if not created:
            WeChatUser.objects.filter(openid=openid).update(last_seen=now)

        token, expire_at = issue_token(openid)
        return Response({'token': token, 'expireAt': expire_at})


class SyncPullView(CheckinAPIView):
    """``GET /api/checkin/sync/pull/``：拉取当前用户全量数据。"""

    authentication_classes = [WeChatJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [OpenidRateThrottle, IPRateThrottle]

    def get(self, request):
        """返回当前 openid 的快照。

        Args:
            request (Request): 已通过鉴权的请求。

        Returns:
            Response: 有数据返回 ``{version, updatedAt, payload}``；
            从没同步过时返回 ``{version:0, updatedAt:null, payload:null}``。
        """
        row = SyncSnapshot.objects.filter(openid=request.user.openid).first()
        if row is None or row.payload is None:
            return Response({'version': 0, 'updatedAt': None, 'payload': None})
        return Response({
            'version': row.version,
            'updatedAt': row.updated_at,
            'payload': json.loads(row.payload),
        })


class SyncPushView(CheckinAPIView):
    """``POST /api/checkin/sync/push/``：整包覆盖式上传。"""

    authentication_classes = [WeChatJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [OpenidRateThrottle, IPRateThrottle]

    def post(self, request):
        """整包覆盖当前用户数据，并对 baseVersion 做原子比对。

        Args:
            request (Request): 含 ``baseVersion`` 与 ``payload`` 的请求。

        Returns:
            Response: 成功返回 ``{version, updatedAt}``；版本不一致返回
            ``409`` 并附服务端当前 ``version`` 与完整 ``payload``。
        """
        if _content_length(request) > settings.CHECKIN_PAYLOAD_MAX_BYTES:
            return error_response('payload_too_large', '请求体超过 2MB', status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)

        serializer = PushSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response('invalid_payload', '请求参数不合法', status.HTTP_400_BAD_REQUEST)
        base_version = serializer.validated_data['baseVersion']
        payload = serializer.validated_data['payload']

        openid = request.user.openid
        now = _now_ms()
        with transaction.atomic():
            SyncSnapshot.objects.get_or_create(
                openid=openid,
                defaults={'version': 0, 'payload': None, 'updated_at': None},
            )
            updated = SyncSnapshot.objects.filter(openid=openid, version=base_version).update(
                version=F('version') + 1,
                payload=json.dumps(payload, ensure_ascii=False),
                updated_at=now,
            )
            row = SyncSnapshot.objects.get(openid=openid)

        if updated == 1:
            return Response({'version': row.version, 'updatedAt': now})

        return Response(
            {
                'error': 'version_conflict',
                'message': '版本号不一致',
                'version': row.version,
                'payload': json.loads(row.payload) if row.payload else None,
            },
            status=status.HTTP_409_CONFLICT,
        )
