from django.urls import path

from . import views

app_name = "threads"

urlpatterns = [
    path("", views.thread_list, name="list"),
    path("write/", views.write, name="write"),
    path("<int:pk>/", views.detail, name="detail"),
    path("<int:pk>/like/", views.toggle_like, name="like"),
    path("<int:pk>/delete/", views.delete, name="delete"),
]
