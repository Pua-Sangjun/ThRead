from urllib.parse import urlencode

from django.contrib import messages
from django.http import Http404
from django.core.paginator import Paginator
from django.db.models import Count, F
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from threads.models import Thread

from . import kakao
from .models import TOPICS, Book

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
    # 독자들이 많이 담고 쓰레드를 쓴 책 (ThRead 회원 활동 기준)
    popular_books = list(
        Book.objects.annotate(
            n_archived=Count("archived_by", distinct=True), n_threads=Count("threads", distinct=True)
        )
        .annotate(score=F("n_archived") + F("n_threads"))
        .filter(score__gt=0)
        .order_by("-score", "-id")[:12]
    )
    popular = Thread.objects.with_likes(request.user).order_by("-num_likes", "-id")[:18]
    page = Paginator(popular, 6).get_page(request.GET.get("page"))
    return render(
        request,
        "books/main.html",
        {
            # Carousel 한 장에 4권씩
            "book_slides": [popular_books[i : i + 4] for i in range(0, len(popular_books), 4)],
            "topics": TOPICS,
            "page": page,
        },
    )


def _page_number(request):
    try:
        return max(1, int(request.GET.get("page", 1)))
    except ValueError:
        return 1


def search(request):
    """카카오 책 검색으로 모든 책을 찾는다. (검색어가 없으면 ThRead 에 등록된 책)"""
    q = request.GET.get("q", "").strip()
    context = {"q": q, "topics": [t[0] for t in TOPICS], "error": False}
    if not q:
        context["registered"] = Book.objects.order_by("-id")[:24]
        return render(request, "books/search.html", context)

    page = min(_page_number(request), kakao.MAX_PAGE)
    try:
        found, total, is_end = kakao.search(q, page=page)
    except kakao.KakaoBookError:
        found, total, is_end = [], 0, True
        context["error"] = True
    context.update(
        {
            # 저장 전 결과도 같은 카드 템플릿을 쓰도록 Book 객체로 만든다 (DB 에는 저장하지 않음)
            "books": [Book(**fields) for fields in found],
            "total": total,
            "page": page,
            "prev_page": page - 1 if page > 1 else None,
            "next_page": page + 1 if not is_end and page < kakao.MAX_PAGE else None,
        }
    )
    return render(request, "books/search.html", context)


def _get_or_create_by_isbn(isbn):
    book = Book.objects.filter(isbn=isbn).first()
    if book:
        return book
    try:
        fields = kakao.find_by_isbn(isbn)
    except kakao.KakaoBookError:
        fields = None
    if not fields:
        return None
    # 10자리로 들어와도 카카오가 준 13자리 ISBN 기준으로 저장 (같은 책이 두 번 저장되지 않게)
    book, _ = Book.objects.get_or_create(isbn=fields.pop("isbn"), defaults=fields)
    return book


def detail(request):
    isbn = request.GET.get("isbn", "").strip().replace("-", "")
    title = request.GET.get("title", "").strip()
    if not isbn and title:
        # 예전 주소(?title=)로 들어오면 ISBN 주소로 이동
        book = Book.objects.filter(title=title).order_by("id").first()
        if book is None:
            raise Http404("도서를 찾을 수 없습니다.")
        return redirect(book.get_absolute_url(), permanent=True)
    if not isbn:
        return redirect("books:search")
    book = _get_or_create_by_isbn(isbn)
    if book is None:
        raise Http404("도서를 찾을 수 없습니다.")
    if book.isbn != isbn:
        return redirect(book.get_absolute_url(), permanent=True)

    threads = Thread.objects.with_likes(request.user).filter(book=book)
    page = Paginator(threads, 5).get_page(request.GET.get("page"))
    is_archived = request.user.is_authenticated and book.archived_by.filter(pk=request.user.pk).exists()

    # 이 작가의 다른 책 (카카오 저자 검색, 실패하면 섹션을 숨김)
    author_books = []
    if book.first_author:
        try:
            found, _, _ = kakao.search(book.first_author, target="person", size=12)
            author_books = [Book(**f) for f in found if f["isbn"] != book.isbn and f["title"] != book.title][:6]
        except kakao.KakaoBookError:
            pass

    return render(
        request,
        "books/detail.html",
        {
            "book": book,
            "is_archived": is_archived,
            "page": page,
            # 쓰레드 페이지를 넘긴 경우 쓰레드 탭을 열어 둔다
            "thread_tab": "page" in request.GET,
            "library": LIBRARY,
            "stats": {
                "archived": book.archived_by.count(),
                "threads": page.paginator.count,
                "likes": Thread.liked_by.through.objects.filter(thread__book=book).count(),
            },
            "popular_threads": threads.order_by("-num_likes", "-id")[:3],
            "author_books": author_books,
        },
    )


def detail_by_id(request, pk):
    """예전 주소(/books/2/)로 들어오면 ISBN 주소로 영구 이동 (이미 공유된 링크 보호)"""
    book = get_object_or_404(Book, pk=pk)
    return redirect(book.get_absolute_url(), permanent=True)


@require_POST
def toggle_archive(request, pk):
    book = get_object_or_404(Book, pk=pk)
    detail_url = book.get_absolute_url()
    if not request.user.is_authenticated:
        return login_redirect(detail_url)
    if book.archived_by.filter(pk=request.user.pk).exists():
        book.archived_by.remove(request.user)
        messages.info(request, "담기를 취소했습니다.")
    else:
        book.archived_by.add(request.user)
        messages.success(request, "마이 페이지에 담았습니다.")
    return redirect(detail_url)
