"""checkin 接口的请求参数校验。"""
from rest_framework import serializers

#: payload 最外层必须包含的四个 key 及其类型（不校验内部结构与字段名）
PAYLOAD_TYPES = {
    'checkin_goals_v1': list,
    'checkin_records_v1': dict,
    'expense_categories_v1': list,
    'expense_records_v1': list,
}


class LoginSerializer(serializers.Serializer):
    """``POST /api/checkin/login/`` 的请求体。"""

    code = serializers.CharField(allow_blank=False, trim_whitespace=True)


class PushSerializer(serializers.Serializer):
    """``POST /api/checkin/sync/push/`` 的请求体。"""

    baseVersion = serializers.IntegerField(min_value=0)
    payload = serializers.DictField()

    def validate_payload(self, value):
        """校验 payload 最外层：必须是对象且四个 key 类型正确。

        Args:
            value (dict): 待校验的 payload。

        Returns:
            dict: 校验通过的 payload。

        Raises:
            serializers.ValidationError: 缺少 key 或类型不符。
        """
        for key, expected in PAYLOAD_TYPES.items():
            if key not in value or not isinstance(value[key], expected):
                raise serializers.ValidationError(f'payload 字段 {key} 缺失或类型不合法')
        return value
