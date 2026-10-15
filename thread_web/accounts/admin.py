from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class ThreadUserAdmin(UserAdmin):
    list_display = ("username", "nickname", "kakao_id", "is_staff", "date_joined")
    fieldsets = UserAdmin.fieldsets + (("ThRead", {"fields": ("nickname", "kakao_id", "profile_image")}),)
