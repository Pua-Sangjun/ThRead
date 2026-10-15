from django.urls import path

from . import views

app_name = "books"

urlpatterns = [
    path("", views.main, name="main"),
    path("books/search/", views.search, name="search"),
    path("books/<int:pk>/", views.detail, name="detail"),
    path("books/<int:pk>/archive/", views.toggle_archive, name="archive"),
]
