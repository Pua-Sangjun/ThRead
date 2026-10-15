from django.contrib import admin

from .models import Author, Book


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "author", "genre", "bestseller_rank", "is_ai_pick")
    list_filter = ("genre", "is_ai_pick")
    search_fields = ("title", "author")


admin.site.register(Author)
