"""도서를 카카오 책 검색 기반으로 바꾸기 (1/2): 데이터 정리

1. 과제용 임시 도서 중 아무도 담지 않았고 쓰레드도 없는 책은 지운다.
   (실제 회원의 담기·쓰레드가 붙은 책은 그 기록을 지키기 위해 남긴다)
2. 남은 책 중 ISBN 이 없는 책에는 임시 값을 넣고, 직접 만든 임시 표지는 기본 표지로 바꾼다.

PostgreSQL 은 같은 트랜잭션 안에서 행을 지운 뒤 바로 ALTER TABLE 을 하면
"pending trigger events" 오류가 나므로, 구조 변경은 다음 마이그레이션(0004)으로 나눈다.
"""
from django.db import migrations


def remove_unused_sample_books(apps, schema_editor):
    Book = apps.get_model("books", "Book")
    Thread = apps.get_model("threads", "Thread")
    used = set(Thread.objects.values_list("book_id", flat=True))
    used |= set(Book.archived_by.through.objects.values_list("book_id", flat=True))
    Book.objects.exclude(pk__in=used).delete()
    for book in Book.objects.filter(isbn=""):
        book.isbn = f"NOISBN{book.pk}"
        book.save(update_fields=["isbn"])
    # 직접 만든 임시 표지는 없애고 기본 표지(빈 값)로
    Book.objects.exclude(cover__startswith="http").update(cover="")


class Migration(migrations.Migration):
    dependencies = [
        ("books", "0002_book_isbn_cover"),
        ("threads", "0004_thread_images_webp"),
    ]

    operations = [
        migrations.RunPython(remove_unused_sample_books, migrations.RunPython.noop),
    ]
