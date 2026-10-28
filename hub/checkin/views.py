"""checkin 云同步接口：login / sync.pull / sync.push / space 系列。"""
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
from .models import Space, SpaceCode, SyncSnapshot, WeChatUser
from .serializers import LoginSerializer, PushSerializer, SpaceJoinSerializer
from .throttles import IPRateThrottle, OpenidRateThrottle, SpaceCodeThrottle, SpaceJoinThrottle
from .wechat import WeChatAPIError, jscode2session

logger = logging.getLogger('checkin')

#: 单个空间的最大成员数
SPACE_MEMBER_LIMIT = 5

#: 绑定码有效期（秒）
SPACE_CODE_TTL_SECONDS = 600


def _now_ms():
    """返回当前毫秒时间戳。

    Returns:
        int: 与 ``Date.now()`` 对齐的毫秒时间戳。
    """
    return int(time.time() * 1000)


def _now_s():
    """返回当前 Unix 秒时间戳。

    Returns:
        int: Unix 秒。
    """
    return int(time.time())


def _ensure_space(user):
    """保证用户有所属空间，没有则创建单人空间。

    Args:
        user (WeChatUser): 当前用户。

    Returns:
        Space: 用户所属空间。
    """
    if user.space_id:
        return user.space
    space = Space.objects.create(owner_openid=user.openid, created_at=_now_ms())
    WeChatUser.objects.filter(openid=user.openid).update(space=space)
    user.space = space
    return space


def _member_count(space_id):
    """统计空间成员数。

    Args:
        space_id (str): 空间 ID。

    Returns:
        int: 成员数量。
    """
    return WeChatUser.objects.filter(space_id=space_id).count()


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
        user, created = WeChatUser.objects.get_or_create(
            openid=openid,
            defaults={'created_at': now, 'last_seen': now},
        )
        if not created:
            WeChatUser.objects.filter(openid=openid).update(last_seen=now)
        _ensure_space(user)

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
        row = SyncSnapshot.objects.filter(space_id=request.user.space_id).first()
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

        space_id = request.user.space_id
        now = _now_ms()
        with transaction.atomic():
            SyncSnapshot.objects.get_or_create(
                space_id=space_id,
                defaults={'version': 0, 'payload': None, 'updated_at': None},
            )
            updated = SyncSnapshot.objects.filter(space_id=space_id, version=base_version).update(
                version=F('version') + 1,
                payload=json.dumps(payload, ensure_ascii=False),
                updated_at=now,
            )
            row = SyncSnapshot.objects.get(space_id=space_id)

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


class SpaceBaseView(CheckinAPIView):
    """space 系列接口基类：统一鉴权与限流。"""

    authentication_classes = [WeChatJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [OpenidRateThrottle, IPRateThrottle]


class SpaceInfoView(SpaceBaseView):
    """``GET /api/checkin/space/``：查询当前用户所在空间。"""

    def get(self, request):
        """返回空间 ID、成员数、是否创建者。

        Args:
            request (Request): 已通过鉴权的请求。

        Returns:
            Response: ``{spaceId, memberCount, isOwner, createdAt}``。
        """
        space = _ensure_space(request.user)
        return Response({
            'spaceId': space.id,
            'memberCount': _member_count(space.id),
            'isOwner': space.owner_openid == request.user.openid,
            'createdAt': space.created_at,
        })


class SpaceCodeCreateView(SpaceBaseView):
    """``POST /api/checkin/space/code/``：生成一次性绑定码（6 位数字，10 分钟）。"""

    throttle_classes = [SpaceCodeThrottle, IPRateThrottle]

    def post(self, request):
        """为当前空间生成绑定码；同空间重复生成时旧码立即作废。

        Args:
            request (Request): 已通过鉴权的请求，请求体可为空。

        Returns:
            Response: ``{code, expireAt}``；空间已满返回 409。
        """
        space = _ensure_space(request.user)
        if _member_count(space.id) >= SPACE_MEMBER_LIMIT:
            return error_response('space_full', '空间成员已满', status.HTTP_409_CONFLICT)

        now = _now_s()
        with transaction.atomic():
            SpaceCode.objects.filter(space_id=space.id, used_at__isnull=True).update(used_at=now)
            code_obj = SpaceCode.objects.create(space_id=space.id, expire_at=now + SPACE_CODE_TTL_SECONDS)
        return Response({'code': code_obj.code, 'expireAt': code_obj.expire_at})


class SpaceJoinView(SpaceBaseView):
    """``POST /api/checkin/space/join/``：凭绑定码加入空间。"""

    throttle_classes = [SpaceJoinThrottle, IPRateThrottle]

    def post(self, request):
        """校验绑定码并把用户改挂到目标空间，**不动任何快照**。

        Args:
            request (Request): 含 ``code`` 的请求。

        Returns:
            Response: 成功返回 ``{spaceId, memberCount}``；各类失败见文档 13.3③。
        """
        serializer = SpaceJoinSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response('invalid_space_code', '绑定码格式不正确', status.HTTP_400_BAD_REQUEST)
        code = serializer.validated_data['code']

        now = _now_s()
        with transaction.atomic():
            code_obj = SpaceCode.objects.select_for_update().filter(pk=code).first()
            if code_obj is None:
                return error_response('invalid_space_code', '绑定码不存在', status.HTTP_400_BAD_REQUEST)
            if code_obj.expire_at <= now:
                return error_response('space_code_expired', '绑定码已过期', status.HTTP_410_GONE)
            if code_obj.used_at is not None:
                return error_response('space_code_used', '绑定码已被使用', status.HTTP_409_CONFLICT)

            user = WeChatUser.objects.select_for_update().get(pk=request.user.openid)
            _ensure_space(user)
            if user.space_id == code_obj.space_id:
                return error_response('already_in_space', '已在该空间中', status.HTTP_409_CONFLICT)
            if _member_count(code_obj.space_id) >= SPACE_MEMBER_LIMIT:
                return error_response('space_full', '空间成员已满', status.HTTP_409_CONFLICT)

            user.space_id = code_obj.space_id
            user.save(update_fields=['space_id'])
            code_obj.used_at = now
            code_obj.save(update_fields=['used_at'])

        return Response({'spaceId': code_obj.space_id, 'memberCount': _member_count(code_obj.space_id)})


class SpaceLeaveView(SpaceBaseView):
    """``POST /api/checkin/space/leave/``：退出当前空间。"""

    def post(self, request):
        """为调用者新建单人空间并把当前共享快照复制过去。

        最后一名成员退出时原地保留，不新建空间。

        Args:
            request (Request): 已通过鉴权的请求，请求体为空。

        Returns:
            Response: ``{spaceId, memberCount}``。
        """
        with transaction.atomic():
            user = WeChatUser.objects.select_for_update().get(pk=request.user.openid)
            if not user.space_id:
                return error_response('not_in_space', '当前不在任何空间中', status.HTTP_409_CONFLICT)

            old_space_id = user.space_id
            if _member_count(old_space_id) <= 1:
                return Response({'spaceId': old_space_id, 'memberCount': 1})

            new_space = Space.objects.create(owner_openid=user.openid, created_at=_now_ms())
            old_snapshot = SyncSnapshot.objects.filter(space_id=old_space_id).first()
            if old_snapshot is not None:
                SyncSnapshot.objects.create(
                    space_id=new_space.id,
                    version=old_snapshot.version,
                    payload=old_snapshot.payload,
                    updated_at=old_snapshot.updated_at,
                )
            user.space_id = new_space.id
            user.save(update_fields=['space_id'])

        return Response({'spaceId': new_space.id, 'memberCount': 1})
