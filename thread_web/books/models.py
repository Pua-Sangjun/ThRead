from django.conf import settings
from django.db import models

# 장르: (이름, 메인 Grid 영역 클래스, 이미지) — 메인 페이지 장르 Grid 순서와 동일
GENRES = [
    ("여행", "travel", "genre/travel.jpg"),
    ("건강", "health", "genre/health.jpg"),
    ("예술", "art", "genre/art.jpg"),
    ("역사", "history", "genre/history.jpg"),
    ("로맨스", "romance", "genre/romance.jpg"),
    ("철학", "philosophy", "genre/philosophy.jpg"),
    ("자연과학", "science", "genre/natural_science.jpg"),
    ("유아", "baby", "genre/baby.jpg"),
    ("청소년", "youth", "genre/youth.jpg"),
    ("경제", "economy", "genre/economy.jpg"),
]
GENRE_CHOICES = [(name, name) for name, _, _ in GENRES]


class Author(models.Model):
    name = models.CharField("이름", max_length=50, unique=True)
    bio = models.TextField("소개")

    def __str__(self):
        return self.name


class Book(models.Model):
    title = models.CharField("제목", max_length=100)
    author = models.CharField("작가", max_length=50, blank=True)
    publisher = models.CharField("출판사", max_length=50, blank=True)
    year = models.PositiveSmallIntegerField("출간 연도", null=True, blank=True)
    genre = models.CharField("장르", max_length=10, choices=GENRE_CHOICES)
    cover = models.CharField("표지 (static 경로)", max_length=200)
    description = models.TextField("소개")
    bestseller_rank = models.PositiveSmallIntegerField("베스트셀러 순위", null=True, blank=True)
    is_ai_pick = models.BooleanField("AI 추천", default=False)
    archived_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="archived_books", blank=True, verbose_name="담은 회원"
    )

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.title

    @property
    def meta(self):
        """'한강 · 창비 · 2007 · 철학' 처럼 비어 있지 않은 정보만 이어 붙인다."""
        return " · ".join(str(v) for v in (self.author, self.publisher, self.year, self.genre) if v and v != "-")

    @property
    def short_meta(self):
        return " · ".join(v for v in (self.author, self.genre) if v and v != "-")

    @property
    def author_info(self):
        return Author.objects.filter(name=self.author).first()
