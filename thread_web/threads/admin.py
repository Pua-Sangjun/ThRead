from django.contrib import admin

from .models import Thread


@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "book", "user", "seed_likes", "created_at")
    list_filter = ("book",)
    search_fields = ("title", "body")
