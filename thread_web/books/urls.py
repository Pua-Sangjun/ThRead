from django.urls import path

from . import views

app_name = "books"

urlpatterns = [
    path("", views.main, name="main"),
    path("books/search/", views.search, name="search"),
    path("books/", views.detail, name="detail"),  # ?title=책 제목
    path("books/<int:pk>/", views.detail_by_id, name="detail_by_id"),  # 예전 주소 → 새 주소로 이동
    path("books/<int:pk>/archive/", views.toggle_archive, name="archive"),
]
