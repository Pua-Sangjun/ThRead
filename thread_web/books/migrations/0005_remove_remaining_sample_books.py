"""과제용 임시 도서를 남김없이 지운다.

0003 에서는 회원의 담기·쓰레드가 붙은 임시 도서를 남겼지만, 모두 지우기로 했다.
임시 도서는 과제 데이터의 ISBN(13권)과, ISBN 이 없어 임시 값을 넣은 책(NOISBN…)으로만 찾는다.
지운 책에 달린 쓰레드·좋아요·담기 기록도 함께 지워진다.
"""
from django.db import migrations

SAMPLE_ISBNS = [
    "9788936434120",  # 소년이 온다
    "9788936434595",  # 채식주의자
    "9788936439651",  # 대온실 수리 보고서
    "9788937473401",  # 급류
    "9791130662596",  # 시간의 계곡
    "9788937461033",  # 인간 실격
    "9788937434488",  # 노르웨이의 숲
    "9791170612216",  # 정원에 대하여
    "9791198896902",  # 네 칼이 센가, 내 칼이 센가
    "9788937479854",  # 새벽의 사원
    "9788998441012",  # 모순
    "9783836565547",  # Bauhaus
    "9783822858738",  # Design of the 20th Century
]


def remove_sample_books(apps, schema_editor):
    Book = apps.get_model("books", "Book")
    Book.objects.filter(isbn__in=SAMPLE_ISBNS).delete()
    Book.objects.filter(isbn__startswith="NOISBN").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("books", "0004_kakao_books_schema"),
        ("threads", "0004_thread_images_webp"),
    ]

    operations = [migrations.RunPython(remove_sample_books, migrations.RunPython.noop)]
