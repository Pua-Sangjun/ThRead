from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """ThRead 회원. 일반 가입(아이디·비밀번호)과 카카오 로그인을 모두 지원한다."""

    nickname = models.CharField("닉네임", max_length=20, blank=True)
    kakao_id = models.BigIntegerField("카카오 회원번호", null=True, blank=True, unique=True)
    profile_image = models.URLField("프로필 이미지", blank=True)

    @property
    def display_name(self):
        return self.nickname or self.username

    @property
    def is_kakao(self):
        return self.kakao_id is not None

    def __str__(self):
        return self.display_name
