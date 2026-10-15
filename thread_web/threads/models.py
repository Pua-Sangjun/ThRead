from django.conf import settings
from django.db import models
from django.templatetags.static import static
from django.db.models import Count, Exists, OuterRef, Value

from books.models import Book

# 쓰레드 대표 이미지로 고를 수 있는 기본 이미지 (빈 값이면 도서 표지 사용)
THREAD_IMAGES = [f"threads/img{n}.webp" for n in range(1, 7)]


class ThreadQuerySet(models.QuerySet):
    def with_likes(self, user=None):
        """좋아요 수(num_likes)와 현재 회원의 좋아요 여부(is_liked)를 함께 조회한다."""
        # 집계(GROUP BY) 쿼리에서는 Meta.ordering 이 적용되지 않으므로 정렬을 직접 지정
        qs = (
            self.select_related("book", "user")
            .annotate(num_likes=Count("liked_by"))
            .order_by(*Thread._meta.ordering)
        )
        if user is not None and user.is_authenticated:
            liked = Thread.liked_by.through.objects.filter(thread_id=OuterRef("pk"), user_id=user.pk)
            return qs.annotate(is_liked=Exists(liked))
        return qs.annotate(is_liked=Value(False))


class Thread(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="threads", verbose_name="도서")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="threads", verbose_name="작성자"
    )
    title = models.CharField("제목", max_length=60)
    body = models.TextField("내용")
    image = models.CharField("대표 이미지 (static 경로, 비우면 도서 표지)", max_length=200, blank=True)
    liked_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="liked_threads", blank=True, verbose_name="좋아요한 회원"
    )
    created_at = models.DateTimeField("작성일", auto_now_add=True)

    objects = ThreadQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return self.title

    @property
    def uses_cover(self):
        return not self.image

    @property
    def image_url(self):
        return static(self.image) if self.image else self.book.cover_url
