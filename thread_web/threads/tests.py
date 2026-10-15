from importlib import import_module
from pathlib import Path

from django.apps import apps
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from books.models import Book

from .models import Thread


def make_threads():
    """채식주의자(2번)에 쓰레드 3개(좋아요 3·2·1), 소년이 온다(1번)에 1개를 만든다."""
    users = [User.objects.create_user(f"reader{i}", password="thread-pass-123", nickname=f"독자{i}") for i in range(3)]
    vegetarian = Book.objects.get(pk=2)
    threads = [
        Thread.objects.create(book=vegetarian, user=users[i], title=f"채식주의자 감상 {i}", body=f"본문 {i}")
        for i in range(3)
    ]
    for i, t in enumerate(threads):
        t.liked_by.add(*users[: 3 - i])
    other = Thread.objects.create(book_id=1, user=users[0], title="소년이 온다 감상", body="본문")
    return users, threads, other


class PageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("load_books", verbosity=0)
        cls.users, cls.threads, cls.other_thread = make_threads()

    def test_public_pages_render(self):
        for url in ["/", "/books/search/", "/books/search/?genre=철학&q=한", "/books/?title=채식주의자",
                    "/books/?title=채식주의자&page=1", "/threads/", "/threads/?book=2&sort=likes",
                    f"/threads/{self.threads[0].pk}/", reverse("accounts:login"), reverse("accounts:signup")]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_not_found_page(self):
        for url in ["/no-such-page/", "/books/999/", "/books/?title=없는책", "/threads/999/"]:
            with self.subTest(url=url):
                res = self.client.get(url)
                self.assertEqual(res.status_code, 404)
                self.assertContains(res, "요청하신 페이지를 찾을 수 없어요", status_code=404)

    def test_main_shows_popular_threads_by_likes(self):
        res = self.client.get("/")
        self.assertEqual([t.num_likes for t in res.context["page"]], [3, 2, 1, 0])
        self.assertEqual(len(res.context["bestseller_slides"]), 3)

    def test_search_filters(self):
        res = self.client.get("/books/search/", {"q": "한강"})
        self.assertEqual({b.title for b in res.context["books"]}, {"소년이 온다", "채식주의자"})
        res = self.client.get("/books/search/", {"genre": "예술"})
        self.assertEqual(len(res.context["books"]), 2)

    def test_book_detail_threads_tab(self):
        res = self.client.get("/books/?title=채식주의자")
        self.assertEqual(res.context["book"].pk, 2)
        self.assertEqual(res.context["page"].paginator.count, 3)
        self.assertContains(res, "1970년 광주에서")  # 작가 소개
        self.assertFalse(res.context["thread_tab"])
        self.assertTrue(self.client.get("/books/?title=채식주의자&page=1").context["thread_tab"])

    def test_book_detail_url_uses_title(self):
        book = Book.objects.get(pk=2)
        self.assertEqual(book.get_absolute_url(), "/books/?title=%EC%B1%84%EC%8B%9D%EC%A3%BC%EC%9D%98%EC%9E%90")
        # 예전 주소는 새 주소로 영구 이동, 제목 없이 오면 검색으로
        self.assertRedirects(self.client.get("/books/2/"), book.get_absolute_url(), status_code=301)
        self.assertRedirects(self.client.get("/books/"), "/books/search/")
        # 목록·카드 링크가 새 주소를 쓴다
        self.assertContains(self.client.get("/"), f'href="{book.get_absolute_url()}"')
        self.assertContains(self.client.get(f"/threads/{self.threads[0].pk}/"), f'href="{book.get_absolute_url()}"')
        # 쓰레드가 5개를 넘어 페이지가 나뉘어도 페이지 링크에 제목이 유지된다
        for i in range(3):
            Thread.objects.create(book=book, user=self.users[0], title=f"추가 {i}", body="본문")
        self.assertContains(self.client.get(book.get_absolute_url()), "?title=%EC%B1%84%EC%8B%9D%EC%A3%BC%EC%9D%98%EC%9E%90&amp;page=2")

    def test_book_detail_stats_and_sections(self):
        res = self.client.get("/books/?title=채식주의자")
        self.assertEqual(res.context["stats"], {"archived": 0, "threads": 3, "likes": 3 + 2 + 1})
        self.assertEqual([t.num_likes for t in res.context["popular_threads"]], [3, 2, 1])
        similar = res.context["similar_books"]
        self.assertEqual(len(similar), 6)
        self.assertNotIn(2, [b.pk for b in similar])
        self.assertEqual([b.genre for b in similar[:3]], ["철학"] * 3)  # 같은 장르 먼저
        self.assertContains(res, "이 책의 인기 쓰레드")
        # 쓰레드가 없는 책은 첫 쓰레드 안내
        self.assertContains(self.client.get("/books/?title=Bauhaus"), "아직 이 책의 쓰레드가 없어요")


class ImageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("load_books", verbosity=0)

    def test_covers_use_kakao_or_own_images(self):
        vegetarian = Book.objects.get(pk=2)
        self.assertEqual(vegetarian.isbn, "9788936434595")
        self.assertTrue(vegetarian.cover_url.startswith("https://search1.kakaocdn.net/"))
        # 카카오에 없는 책은 직접 만든 표지 (static)
        self.assertEqual(Book.objects.get(pk=11).cover_url, "/static/covers/wishing-day.webp")
        # 모든 표지가 카카오 주소이거나 static 안에 실제로 있는 파일
        static_dir = Path(__file__).resolve().parent.parent / "static"
        for b in Book.objects.all():
            with self.subTest(book=b.title):
                self.assertTrue(b.cover.startswith("https://") or (static_dir / b.cover).is_file(), b.cover)

    def test_site_images_exist(self):
        from books.models import GENRES

        from .models import THREAD_IMAGES

        static_dir = Path(__file__).resolve().parent.parent / "static"
        for rel in [g[2] for g in GENRES] + THREAD_IMAGES + ["nav/hero.webp"]:
            with self.subTest(rel=rel):
                self.assertTrue((static_dir / rel).is_file())

    def test_thread_image_url(self):
        user = User.objects.create_user("img")
        own = Thread.objects.create(book_id=2, user=user, title="a", body="b", image="threads/img3.webp")
        self.assertEqual(own.image_url, "/static/threads/img3.webp")
        self.assertContains(self.client.get(f"/threads/{own.pk}/"), 'src="/static/threads/img3.webp"')

    def test_old_jpg_paths_are_migrated(self):
        user = User.objects.create_user("old")
        t = Thread.objects.create(book_id=2, user=user, title="a", body="b", image="threads/img2.jpg")
        import_module("threads.migrations.0004_thread_images_webp").jpg_to_webp(apps, None)
        t.refresh_from_db()
        self.assertEqual(t.image, "threads/img2.webp")


class EmptySiteTests(TestCase):
    """도서만 있고 쓰레드가 하나도 없는 실제 배포 직후 상태"""

    @classmethod
    def setUpTestData(cls):
        call_command("load_books", verbosity=0)

    def test_pages_render_without_threads(self):
        self.assertContains(self.client.get("/"), "아직 쓰레드가 없습니다.")
        self.assertContains(self.client.get("/threads/"), "첫 쓰레드를 작성해 보세요")
        res = self.client.get("/books/?title=채식주의자")
        self.assertEqual(res.context["stats"], {"archived": 0, "threads": 0, "likes": 0})


class RemoveSampleDataMigrationTests(TestCase):
    def test_removes_only_passwordless_sample_users(self):
        call_command("load_books", verbosity=0)
        sample = User.objects.create(username="sample_김독자", nickname="김독자")
        sample.set_unusable_password()
        sample.save()
        Thread.objects.create(book_id=1, user=sample, title="샘플", body="본문")
        real = User.objects.create_user("sample_real", password="thread-pass-123")  # 일반 가입 회원
        Thread.objects.create(book_id=1, user=real, title="진짜", body="본문")

        import_module("threads.migrations.0002_remove_sample_threads").remove_sample_data(apps, None)

        self.assertFalse(User.objects.filter(pk=sample.pk).exists())
        self.assertEqual(list(Thread.objects.values_list("title", flat=True)), ["진짜"])
        self.assertTrue(User.objects.filter(pk=real.pk).exists())


class ActionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("load_books", verbosity=0)
        cls.user = User.objects.create_user("reader", password="thread-pass-123", nickname="독자")
        cls.other = User.objects.create_user("other", password="thread-pass-123", nickname="다른독자")
        cls.thread = Thread.objects.create(book_id=2, user=cls.other, title="감상", body="본문")

    def test_anonymous_actions_redirect_to_login(self):
        res = self.client.post(reverse("books:archive", args=[2]))
        self.assertRedirects(res, "/accounts/login/?next=%2Fbooks%2F%3Ftitle%3D%25EC%25B1%2584%25EC%258B%259D%25EC%25A3%25BC%25EC%259D%2598%25EC%259E%2590",
                             fetch_redirect_response=False)
        res = self.client.post(reverse("threads:like", args=[self.thread.pk]))
        self.assertRedirects(res, f"/accounts/login/?next=%2Fthreads%2F{self.thread.pk}%2F", fetch_redirect_response=False)
        res = self.client.get(reverse("threads:write"))
        self.assertEqual(res.status_code, 302)

    def test_archive_toggle(self):
        self.client.force_login(self.user)
        res = self.client.post(reverse("books:archive", args=[2]))
        self.assertRedirects(res, Book.objects.get(pk=2).get_absolute_url())
        self.assertTrue(Book.objects.get(pk=2).archived_by.filter(pk=self.user.pk).exists())
        self.assertContains(self.client.get("/books/?title=채식주의자"), "담음")
        self.assertContains(self.client.get("/mypage/"), "채식주의자")
        self.client.post(reverse("books:archive", args=[2]))
        self.assertFalse(Book.objects.get(pk=2).archived_by.exists())

    def test_like_toggle_counts(self):
        url = reverse("threads:like", args=[self.thread.pk])
        self.client.force_login(self.user)
        self.client.post(url)
        self.client.force_login(self.other)
        self.client.post(url)
        t = Thread.objects.with_likes(self.other).get(pk=self.thread.pk)
        self.assertEqual(t.num_likes, 2)
        self.assertTrue(t.is_liked)
        # 마이 페이지 '좋아요한 쓰레드'에서도 전체 좋아요 수가 나와야 함
        liked = self.client.get("/mypage/").context["liked"]
        self.assertEqual(liked[0].num_likes, 2)
        self.client.post(url)
        self.assertEqual(Thread.objects.with_likes().get(pk=self.thread.pk).num_likes, 1)

    def test_write_and_delete_thread(self):
        self.client.force_login(self.user)
        self.assertContains(self.client.get(reverse("threads:write") + "?book=3"), 'value="3" selected')
        res = self.client.post(
            reverse("threads:write"),
            {"book": 3, "image": "", "title": "  새 쓰레드  ", "body": "본문입니다"},
        )
        thread = Thread.objects.get(title="새 쓰레드")
        self.assertRedirects(res, reverse("threads:detail", args=[thread.pk]))
        self.assertEqual(thread.image_url, Book.objects.get(pk=3).cover_url)  # 이미지를 안 고르면 도서 표지
        self.assertContains(self.client.get(reverse("threads:detail", args=[thread.pk])), "삭제")

        # 다른 회원은 삭제 불가
        self.client.force_login(self.other)
        self.assertNotContains(self.client.get(reverse("threads:detail", args=[thread.pk])), "bi-trash")
        self.assertEqual(self.client.post(reverse("threads:delete", args=[thread.pk])).status_code, 403)

        self.client.force_login(self.user)
        self.assertRedirects(self.client.post(reverse("threads:delete", args=[thread.pk])), reverse("threads:list"))
        self.assertFalse(Thread.objects.filter(pk=thread.pk).exists())

    def test_write_validation(self):
        self.client.force_login(self.user)
        res = self.client.post(reverse("threads:write"), {"book": 3, "image": "evil.jpg", "title": "", "body": "  "})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(set(res.context["form"].errors), {"image", "title", "body"})

    def test_escapes_user_content(self):
        self.client.force_login(self.user)
        self.client.post(reverse("threads:write"), {"book": 1, "image": "", "title": "<script>x</script>", "body": "b"})
        res = self.client.get("/threads/")
        self.assertNotContains(res, "<script>x</script>")
        self.assertContains(res, "&lt;script&gt;x&lt;/script&gt;")
