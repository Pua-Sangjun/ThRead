from urllib.parse import urlencode

from django.conf import settings
from django.db import models
from django.templatetags.static import static
from django.urls import reverse

# 메인 '주제별 도서' Grid: (검색어, Grid 영역 클래스, 이미지). 누르면 카카오 책 검색으로 이어진다.
TOPICS = [
    ("여행", "travel", "genre/travel.webp"),
    ("건강", "health", "genre/health.webp"),
    ("예술", "art", "genre/art.webp"),
    ("역사", "history", "genre/history.webp"),
    ("로맨스", "romance", "genre/romance.webp"),
    ("철학", "philosophy", "genre/philosophy.webp"),
    ("자연과학", "science", "genre/natural_science.webp"),
    ("유아", "baby", "genre/baby.webp"),
    ("청소년", "youth", "genre/youth.webp"),
    ("경제", "economy", "genre/economy.webp"),
]

NO_COVER = "covers/no-cover.webp"  # 카카오에 표지가 없는 책


class Book(models.Model):
    """카카오 책 검색에서 누군가 상세 페이지를 연 책. (담기·쓰레드를 붙이기 위해 저장)"""

    isbn = models.CharField("ISBN", max_length=13, unique=True)
    title = models.CharField("제목", max_length=300)
    author = models.CharField("저자", max_length=300, blank=True)
    publisher = models.CharField("출판사", max_length=100, blank=True)
    year = models.PositiveSmallIntegerField("출간 연도", null=True, blank=True)
    cover = models.CharField("표지 주소", max_length=500, blank=True)  # 카카오 썸네일 주소
    description = models.TextField("소개", blank=True)
    archived_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="archived_books", blank=True, verbose_name="담은 회원"
    )

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.title

    @property
    def cover_url(self):
        if not self.cover:
            return static(NO_COVER)
        return self.cover if self.cover.startswith(("http://", "https://")) else static(self.cover)

    def get_absolute_url(self):
        """상세 페이지 주소: /books/?isbn=9788936434595"""
        return f"{reverse('books:detail')}?{urlencode({'isbn': self.isbn})}"

    @property
    def meta(self):
        """'한강 · 창비 · 2007' 처럼 비어 있지 않은 정보만 이어 붙인다."""
        return " · ".join(str(v) for v in (self.author, self.publisher, self.year) if v)

    @property
    def short_meta(self):
        return " · ".join(v for v in (self.author, self.publisher) if v)

    @property
    def first_author(self):
        return self.author.split(",")[0].strip()
