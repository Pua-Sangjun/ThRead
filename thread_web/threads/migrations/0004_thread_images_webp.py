"""쓰레드 대표 이미지를 직접 만든 그래픽(threads/imgN.webp)으로 교체하면서, 저장된 옛 경로(.jpg)를 바꾼다."""
from django.db import migrations


def jpg_to_webp(apps, schema_editor):
    Thread = apps.get_model("threads", "Thread")
    for n in range(1, 7):
        Thread.objects.filter(image=f"threads/img{n}.jpg").update(image=f"threads/img{n}.webp")


def webp_to_jpg(apps, schema_editor):
    Thread = apps.get_model("threads", "Thread")
    for n in range(1, 7):
        Thread.objects.filter(image=f"threads/img{n}.webp").update(image=f"threads/img{n}.jpg")


class Migration(migrations.Migration):
    dependencies = [("threads", "0003_remove_seed_likes")]

    operations = [migrations.RunPython(jpg_to_webp, webp_to_jpg)]
