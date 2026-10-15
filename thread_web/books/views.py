from urllib.parse import urlencode

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import F, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from threads.models import Thread

from .models import GENRES, Book

# 도서 상세 > 대여 가능 도서관 (카카오맵)
LIBRARY = {
    "name": "국립중앙도서관",
    "address": "서울 서초구 반포대로 201",
    "lat": 37.49796,
    "lng": 127.00525,
}


def login_redirect(path):
    """로그인이 필요한 동작에서 로그인 후 돌아올 주소와 함께 로그인 페이지로 보낸다."""
    return redirect(f"{reverse('accounts:login')}?{urlencode({'next': path})}")


def main(request):
    bestsellers = list(Book.objects.filter(bestseller_rank__isnull=False).order_by("bestseller_rank")[:12])
    popular = Thread.objects.with_likes(request.user).order_by("-num_likes", "id")[:18]
    page = Paginator(popular, 6).get_page(request.GET.get("page"))
    return render(
        request,
        "books/main.html",
        {
            # Carousel 한 장에 4권씩
            "bestseller_slides": [bestsellers[i : i + 4] for i in range(0, len(bestsellers), 4)],
            "ai_picks": Book.objects.filter(is_ai_pick=True),
            "genres": GENRES,
            "page": page,
        },
    )


def search(request):
    q = request.GET.get("q", "").strip()
    genre = request.GET.get("genre", "")
    books = Book.objects.all()
    if q:
        books = books.filter(Q(title__icontains=q) | Q(author__icontains=q))
    if genre:
        books = books.filter(genre=genre)
    return render(
        request,
        "books/search.html",
        {"books": books, "q": q, "genre": genre, "genres": [g[0] for g in GENRES]},
    )


def detail(request, pk):
    book = get_object_or_404(Book, pk=pk)
    threads = Thread.objects.with_likes(request.user).filter(book=book)
    page = Paginator(threads, 5).get_page(request.GET.get("page"))
    is_archived = request.user.is_authenticated and book.archived_by.filter(pk=request.user.pk).exists()

    # 같은 장르의 책을 먼저, 모자라면 베스트셀러 순으로 채워 6권
    similar = list(Book.objects.filter(genre=book.genre).exclude(pk=book.pk)[:6])
    if len(similar) < 6:
        similar += Book.objects.exclude(pk__in=[book.pk, *(b.pk for b in similar)]).order_by(
            F("bestseller_rank").asc(nulls_last=True), "id"
        )[: 6 - len(similar)]

    return render(
        request,
        "books/detail.html",
        {
            "book": book,
            "author_info": book.author_info,
            "is_archived": is_archived,
            "page": page,
            # 쓰레드 페이지를 넘긴 경우 쓰레드 탭을 열어 둔다
            "thread_tab": "page" in request.GET,
            "library": LIBRARY,
            "stats": {
                "archived": book.archived_by.count(),
                "threads": page.paginator.count,
                # 샘플 좋아요 수 + 실제 회원 좋아요 수 (JOIN 으로 중복 합산되지 않게 따로 집계)
                "likes": (Thread.objects.filter(book=book).aggregate(n=Sum("seed_likes"))["n"] or 0)
                + Thread.liked_by.through.objects.filter(thread__book=book).count(),
            },
            "popular_threads": threads.order_by("-num_likes", "-id")[:3],
            "similar_books": similar,
        },
    )


@require_POST
def toggle_archive(request, pk):
    book = get_object_or_404(Book, pk=pk)
    detail_url = reverse("books:detail", args=[pk])
    if not request.user.is_authenticated:
        return login_redirect(detail_url)
    if book.archived_by.filter(pk=request.user.pk).exists():
        book.archived_by.remove(request.user)
        messages.info(request, "담기를 취소했습니다.")
    else:
        book.archived_by.add(request.user)
        messages.success(request, "마이 페이지에 담았습니다.")
    return redirect(detail_url)
