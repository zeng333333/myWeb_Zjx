"""V2 数据空间迁移：快照归属从 openid 提升到 space_id。

步骤：建 spaces / space_codes 表 → users 加 space 外键 → 建新快照表
→ 每个已有用户落一个单人空间（``sp_<openid>``），快照原样搬过去
→ 删旧快照表 → 新表改名为 SyncSnapshot。迁移后老客户端行为与 V1 完全一致。
"""
from django.db import migrations, models
import django.db.models.deletion

from checkin.models import _new_bind_code, _new_space_id


def migrate_to_spaces(apps, schema_editor):
    """把已有用户与快照迁移到各自的单人空间。

    Args:
        apps (Apps): 历史模型注册表。
        schema_editor (BaseDatabaseSchemaEditor): schema 编辑器（未使用）。
    """
    space_model = apps.get_model('checkin', 'Space')
    user_model = apps.get_model('checkin', 'WeChatUser')
    old_snapshot = apps.get_model('checkin', 'SyncSnapshot')
    new_snapshot = apps.get_model('checkin', 'SyncSnapshotV2')

    for user in user_model.objects.all():
        space_id = f'sp_{user.openid}'
        space_model.objects.get_or_create(
            id=space_id,
            defaults={'owner_openid': user.openid, 'created_at': user.created_at},
        )
        user.space_id = space_id
        user.save(update_fields=['space_id'])

    for snap in old_snapshot.objects.all():
        try:
            user = user_model.objects.get(openid=snap.openid)
        except user_model.DoesNotExist:
            continue
        new_snapshot.objects.create(
            space_id=user.space_id,
            version=snap.version,
            payload=snap.payload,
            updated_at=snap.updated_at,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('checkin', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Space',
            fields=[
                ('id', models.CharField(default=_new_space_id, max_length=40, primary_key=True, serialize=False, verbose_name='空间ID')),
                ('owner_openid', models.CharField(max_length=64, verbose_name='创建者openid')),
                ('created_at', models.BigIntegerField(verbose_name='创建时间(毫秒)')),
            ],
            options={'verbose_name': '数据空间', 'verbose_name_plural': '数据空间'},
        ),
        migrations.CreateModel(
            name='SpaceCode',
            fields=[
                ('code', models.CharField(default=_new_bind_code, max_length=6, primary_key=True, serialize=False, verbose_name='绑定码')),
                ('expire_at', models.BigIntegerField(verbose_name='过期时间(Unix秒)')),
                ('used_at', models.BigIntegerField(blank=True, null=True, verbose_name='使用时间(Unix秒)')),
                ('space', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                            related_name='codes', to='checkin.space', verbose_name='目标空间')),
            ],
            options={'verbose_name': '空间绑定码', 'verbose_name_plural': '空间绑定码'},
        ),
        migrations.AddField(
            model_name='wechatuser',
            name='space',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    related_name='members', to='checkin.space', verbose_name='所属空间'),
        ),
        migrations.CreateModel(
            name='SyncSnapshotV2',
            fields=[
                ('space', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE,
                                               primary_key=True, related_name='snapshot',
                                               serialize=False, to='checkin.space', verbose_name='所属空间')),
                ('version', models.IntegerField(default=0, verbose_name='版本号')),
                ('payload', models.TextField(blank=True, null=True, verbose_name='数据快照(JSON)')),
                ('updated_at', models.BigIntegerField(blank=True, null=True, verbose_name='更新时间(毫秒)')),
            ],
            options={'verbose_name': '数据快照', 'verbose_name_plural': '数据快照'},
        ),
        migrations.RunPython(migrate_to_spaces, migrations.RunPython.noop),
        migrations.DeleteModel(name='SyncSnapshot'),
        migrations.RenameModel(old_name='SyncSnapshotV2', new_name='SyncSnapshot'),
    ]
