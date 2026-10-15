from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from accounts import views as account_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    # 카카오 콘솔에 등록한 Redirect URI 그대로 사용 (http://localhost:5500/api/kakao/callback)
    path(settings.KAKAO_REDIRECT_PATH.lstrip("/"), account_views.kakao_callback, name="kakao_callback"),
    path("mypage/", account_views.mypage, name="mypage"),
    path("threads/", include("threads.urls")),
    path("", include("books.urls")),
]
