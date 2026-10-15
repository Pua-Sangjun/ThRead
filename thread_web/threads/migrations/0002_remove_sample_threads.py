"""배포 전 화면 확인용으로 넣었던 샘플 쓰레드와 샘플 작성자 계정을 지운다.

샘플 작성자는 load_sample_data 가 username "sample_<이름>", 비밀번호 없음("!" 로 시작)으로 만들었다.
일반 가입 회원은 비밀번호가 있으므로, 같은 접두사로 가입했더라도 지워지지 않는다.
"""
from django.db import migrations


def remove_sample_data(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    sample_users = User.objects.filter(username__startswith="sample_", password__startswith="!")
    # 쓰레드·좋아요는 작성자 삭제 시 CASCADE 로 함께 지워진다
    sample_users.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
        ("threads", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(remove_sample_data, migrations.RunPython.noop),
    ]
