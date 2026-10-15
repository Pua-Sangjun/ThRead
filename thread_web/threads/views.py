from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.templatetags.static import static
from django.urls import reverse
from django.views.decorators.http import require_POST

from books.models import Book
from books.views import login_redirect

from .forms import ThreadForm
from .models import THREAD_IMAGES, Thread


def thread_list(request):
    threads = Thread.objects.with_likes(request.user)
    book_id = request.GET.get("book", "")
    if book_id.isdigit():
        threads = threads.filter(book_id=book_id)
    else:
        book_id = ""
    sort = request.GET.get("sort", "new")
    if sort == "likes":
        threads = threads.order_by("-num_likes", "-id")
    page = Paginator(threads, 6).get_page(request.GET.get("page"))
    return render(
        request,
        "threads/list.html",
        {"page": page, "books": Book.objects.all(), "book_id": book_id, "sort": sort},
    )


def detail(request, pk):
    thread = get_object_or_404(Thread.objects.with_likes(request.user), pk=pk)
    related = Thread.objects.with_likes(request.user).filter(book=thread.book).exclude(pk=pk)[:3]
    return render(request, "threads/detail.html", {"thread": thread, "related": related})


@login_required
def write(request):
    form = ThreadForm(request.POST or None, initial={"book": request.GET.get("book")})
    if request.method == "POST" and form.is_valid():
        thread = form.save(commit=False)
        thread.user = request.user
        thread.save()
        messages.success(request, "쓰레드를 등록했습니다.")
        return redirect("threads:detail", pk=thread.pk)
    return render(
        request,
        "threads/write.html",
        {
            "form": form,
            "thread_images": THREAD_IMAGES,
            # 도서를 바꿀 때 '표지' 미리보기를 갱신하기 위한 도서 id → 표지 URL
            "covers": {str(b.pk): static(b.cover) for b in Book.objects.all()},
        },
    )


@require_POST
def toggle_like(request, pk):
    thread = get_object_or_404(Thread, pk=pk)
    detail_url = reverse("threads:detail", args=[pk])
    if not request.user.is_authenticated:
        return login_redirect(detail_url)
    if thread.liked_by.filter(pk=request.user.pk).exists():
        thread.liked_by.remove(request.user)
    else:
        thread.liked_by.add(request.user)
    return redirect(detail_url)


@require_POST
def delete(request, pk):
    thread = get_object_or_404(Thread, pk=pk)
    if thread.user_id != request.user.pk:
        return HttpResponseForbidden("본인이 작성한 쓰레드만 삭제할 수 있습니다.")
    thread.delete()
    messages.info(request, "쓰레드를 삭제했습니다.")
    return redirect("threads:list")
