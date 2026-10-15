"""도서를 카카오 책 검색 기반으로 바꾼다.

1. 과제용 임시 도서 중 아무도 담지 않았고 쓰레드도 없는 책은 지운다.
   (실제 회원의 담기·쓰레드가 붙은 책은 그 기록을 지키기 위해 남긴다)
2. 남은 책 중 ISBN 이 없는 책에는 임시 값을 넣고, 직접 만든 임시 표지는 기본 표지로 바꾼다.
3. 카카오가 주지 않는 정보(장르, 베스트셀러 순위, AI 추천, 작가 소개)를 없앤다.
"""
from django.db import migrations, models


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
        migrations.RemoveField(model_name="book", name="genre"),
        migrations.RemoveField(model_name="book", name="bestseller_rank"),
        migrations.RemoveField(model_name="book", name="is_ai_pick"),
        migrations.DeleteModel(name="Author"),
        migrations.AlterModelOptions(name="book", options={"ordering": ["id"]}),
        migrations.AlterField(
            model_name="book", name="isbn", field=models.CharField(max_length=13, unique=True, verbose_name="ISBN")
        ),
        migrations.AlterField(model_name="book", name="title", field=models.CharField(max_length=300, verbose_name="제목")),
        migrations.AlterField(
            model_name="book", name="author", field=models.CharField(blank=True, max_length=300, verbose_name="저자")
        ),
        migrations.AlterField(
            model_name="book", name="publisher", field=models.CharField(blank=True, max_length=100, verbose_name="출판사")
        ),
        migrations.AlterField(
            model_name="book", name="cover", field=models.CharField(blank=True, max_length=500, verbose_name="표지 주소")
        ),
        migrations.AlterField(model_name="book", name="description", field=models.TextField(blank=True, verbose_name="소개")),
    ]
