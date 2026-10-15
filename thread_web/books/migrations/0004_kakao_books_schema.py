"""도서를 카카오 책 검색 기반으로 바꾸기 (2/2): 구조 변경

카카오가 주지 않는 정보(장르, 베스트셀러 순위, AI 추천, 작가 소개)를 없애고 ISBN 을 고유값으로 바꾼다.
"""
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("books", "0003_remove_unused_sample_books")]

    operations = [
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
