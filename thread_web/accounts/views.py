import logging
import secrets

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from threads.models import Thread

from . import kakao
from .forms import LoginForm, SignupForm
from .models import User

logger = logging.getLogger(__name__)


def _safe_next(request, value):
    """같은 사이트 안의 주소만 next 로 허용한다."""
    if value and url_has_allowed_host_and_scheme(value, allowed_hosts={request.get_host()}):
        return value
    return ""


def login_view(request):
    if request.user.is_authenticated:
        return redirect("books:main")
    next_url = _safe_next(request, request.POST.get("next") or request.GET.get("next"))
    form = LoginForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        return redirect(next_url or settings.LOGIN_REDIRECT_URL)
    return render(request, "accounts/login.html", {"form": form, "next": next_url})


def signup_view(request):
    if request.user.is_authenticated:
        return redirect("books:main")
    next_url = _safe_next(request, request.POST.get("next") or request.GET.get("next"))
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(request, f"{user.display_name}님, ThRead에 오신 것을 환영합니다!")
        return redirect(next_url or settings.LOGIN_REDIRECT_URL)
    return render(request, "accounts/signup.html", {"form": form, "next": next_url})


@require_POST
def logout_view(request):
    logout(request)
    return redirect(f"{reverse('accounts:login')}?logout=1")


# ---------- 카카오 로그인 ----------
def _kakao_redirect_uri(request):
    return request.build_absolute_uri(settings.KAKAO_REDIRECT_PATH)


def kakao_login(request):
    if not settings.KAKAO_REST_API_KEY:
        return redirect(f"{reverse('accounts:login')}?error=config")
    state = secrets.token_urlsafe(16)
    # state 와 돌아갈 주소는 세션에 저장 (CSRF 방지)
    request.session["kakao_state"] = state
    request.session["kakao_next"] = _safe_next(request, request.GET.get("next"))
    return redirect(kakao.authorize_url(_kakao_redirect_uri(request), state))


def kakao_callback(request):
    login_url = reverse("accounts:login")
    state = request.session.pop("kakao_state", None)
    next_url = request.session.pop("kakao_next", "")
    if not state or request.GET.get("state") != state:
        return redirect(f"{login_url}?error=state")
    if "error" in request.GET:  # 동의 화면에서 취소
        return redirect(f"{login_url}?error=cancelled")

    try:
        profile = kakao.fetch_profile(request.GET.get("code", ""), _kakao_redirect_uri(request))
    except kakao.KakaoError as e:
        logger.warning("카카오 로그인 실패: %s", e)
        return redirect(f"{login_url}?error=token")

    user, created = User.objects.get_or_create(
        kakao_id=profile["id"],
        defaults={"username": f"kakao_{profile['id']}"},
    )
    if created:
        user.set_unusable_password()
    # 닉네임·프로필 사진은 로그인할 때마다 카카오 정보로 갱신
    user.nickname = profile["nickname"][:20] or user.nickname or f"카카오{str(profile['id'])[-4:]}"
    user.profile_image = profile["image"] if profile["image"].startswith("https://") else ""
    user.save()

    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    if created:
        messages.success(request, f"{user.display_name}님, ThRead에 오신 것을 환영합니다!")
    return redirect(next_url or settings.LOGIN_REDIRECT_URL)


# ---------- 마이 페이지 ----------
@login_required
def mypage(request):
    user = request.user
    archive = user.archived_books.all()
    threads = Thread.objects.with_likes(user)
    mine = threads.filter(user=user)
    # 좋아요 수 집계(annotate) 뒤에 거르므로 다른 회원의 좋아요까지 포함해 셈
    liked = threads.filter(liked_by=user)
    return render(
        request,
        "accounts/mypage.html",
        {"archive": archive, "mine": mine, "liked": liked},
    )
