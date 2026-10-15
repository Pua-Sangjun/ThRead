from unittest import mock

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from . import kakao
from .models import User


class SignupLoginTests(TestCase):
    def test_signup_logs_in_and_redirects_to_next(self):
        res = self.client.post(
            reverse("accounts:signup"),
            {"username": "reader1", "nickname": "책벌레", "password1": "thread-pass-123", "password2": "thread-pass-123",
             "next": "/mypage/"},
        )
        self.assertRedirects(res, "/mypage/")
        user = User.objects.get(username="reader1")
        self.assertEqual(user.display_name, "책벌레")
        self.assertContains(self.client.get("/mypage/"), "책벌레 님")

    def test_login_rejects_external_next(self):
        User.objects.create_user("reader2", password="thread-pass-123")
        res = self.client.post(
            reverse("accounts:login"),
            {"username": "reader2", "password": "thread-pass-123", "next": "https://evil.example/"},
        )
        self.assertRedirects(res, reverse("books:main"), fetch_redirect_response=False)

    def test_wrong_password_shows_error(self):
        User.objects.create_user("reader3", password="thread-pass-123")
        res = self.client.post(reverse("accounts:login"), {"username": "reader3", "password": "nope"})
        self.assertContains(res, "아이디 또는 비밀번호가 올바르지 않습니다.")

    def test_logout_requires_post(self):
        self.assertEqual(self.client.get(reverse("accounts:logout")).status_code, 405)

    def test_mypage_requires_login(self):
        res = self.client.get("/mypage/")
        self.assertRedirects(res, "/accounts/login/?next=/mypage/", fetch_redirect_response=False)


@override_settings(KAKAO_REST_API_KEY="dummy-rest-key", KAKAO_CLIENT_SECRET="dummy-secret")
class KakaoLoginTests(TestCase):
    def start_login(self, next_url="/threads/"):
        res = self.client.get(reverse("accounts:kakao_login"), {"next": next_url})
        self.assertEqual(res.status_code, 302)
        self.assertTrue(res["Location"].startswith(kakao.AUTHORIZE_URL))
        self.assertIn("redirect_uri=http%3A%2F%2Ftestserver%2Fapi%2Fkakao%2Fcallback", res["Location"])
        return self.client.session["kakao_state"]

    def test_login_page_shows_kakao_button(self):
        self.assertContains(self.client.get(reverse("accounts:login")), "카카오 로그인")

    @mock.patch("accounts.kakao.fetch_profile")
    def test_callback_creates_user_and_logs_in(self, fetch_profile):
        fetch_profile.return_value = {"id": 12345, "nickname": "카카오독자", "image": "https://k.kakaocdn.net/p.jpg"}
        state = self.start_login("/threads/")
        res = self.client.get("/api/kakao/callback", {"code": "abc", "state": state})
        self.assertRedirects(res, "/threads/", fetch_redirect_response=False)
        user = User.objects.get(kakao_id=12345)
        self.assertEqual(user.nickname, "카카오독자")
        self.assertFalse(user.has_usable_password())
        page = self.client.get("/mypage/")
        self.assertContains(page, "카카오독자 님")
        self.assertContains(page, "https://k.kakaocdn.net/p.jpg")

        # 두 번째 로그인은 같은 회원을 쓰고 닉네임만 갱신
        fetch_profile.return_value = {"id": 12345, "nickname": "새닉네임", "image": ""}
        state = self.start_login()
        self.client.get("/api/kakao/callback", {"code": "def", "state": state})
        self.assertEqual(User.objects.filter(kakao_id=12345).count(), 1)
        self.assertEqual(User.objects.get(kakao_id=12345).nickname, "새닉네임")

    def test_callback_rejects_forged_state(self):
        self.start_login()
        res = self.client.get("/api/kakao/callback", {"code": "abc", "state": "forged"})
        self.assertRedirects(res, "/accounts/login/?error=state", fetch_redirect_response=False)

    def test_callback_cancelled(self):
        state = self.start_login()
        res = self.client.get("/api/kakao/callback", {"error": "access_denied", "state": state})
        self.assertRedirects(res, "/accounts/login/?error=cancelled", fetch_redirect_response=False)

    @mock.patch("accounts.kakao.fetch_profile", side_effect=kakao.KakaoError("KOE320"))
    def test_callback_token_failure(self, _):
        state = self.start_login()
        res = self.client.get("/api/kakao/callback", {"code": "bad", "state": state})
        self.assertRedirects(res, "/accounts/login/?error=token", fetch_redirect_response=False)

    def test_kakao_login_always_asks_account(self):
        # 다른 카카오 계정으로 바꿔 로그인할 수 있도록 매번 카카오 로그인 화면을 띄운다
        res = self.client.get(reverse("accounts:kakao_login"))
        self.assertIn("prompt=login", res["Location"])

    def test_kakao_user_logout_stays_on_site(self):
        user = User.objects.create(username="kakao_1", kakao_id=1, nickname="카카오회원")
        self.client.force_login(user)
        res = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(res, "/accounts/login/?logout=1", fetch_redirect_response=False)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_password_user_logout_stays_on_site(self):
        user = User.objects.create_user("plain", password="thread-pass-123")
        self.client.force_login(user)
        res = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(res, "/accounts/login/?logout=1", fetch_redirect_response=False)

    def test_external_next_is_dropped(self):
        self.start_login("https://evil.example/")
        self.assertEqual(self.client.session["kakao_next"], "")


@override_settings(KAKAO_REST_API_KEY="")
class KakaoDisabledTests(TestCase):
    def test_no_kakao_button_without_key(self):
        self.assertNotContains(self.client.get(reverse("accounts:login")), "카카오 로그인</a>")

    def test_kakao_login_without_key(self):
        res = self.client.get(reverse("accounts:kakao_login"))
        self.assertRedirects(res, "/accounts/login/?error=config", fetch_redirect_response=False)
