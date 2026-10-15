from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from books.models import Book

from .models import Thread


class PageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("load_sample_data", verbosity=0)

    def test_public_pages_render(self):
        for url in ["/", "/books/search/", "/books/search/?genre=철학&q=한", "/books/?title=채식주의자", "/books/?title=채식주의자&page=1",
                    "/threads/", "/threads/?book=2&sort=likes", "/threads/1/", reverse("accounts:login"),
                    reverse("accounts:signup")]:
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
        titles = [t.title for t in res.context["page"]]
        self.assertEqual(len(titles), 6)
        self.assertEqual(res.context["page"][0].num_likes, 128)
        self.assertEqual(len(res.context["bestseller_slides"]), 3)

    def test_search_filters(self):
        res = self.client.get("/books/search/", {"q": "한강"})
        self.assertEqual({b.title for b in res.context["books"]}, {"소년이 온다", "채식주의자"})
        res = self.client.get("/books/search/", {"genre": "예술"})
        self.assertEqual(len(res.context["books"]), 2)

    def test_book_detail_threads_tab(self):
        res = self.client.get("/books/?title=채식주의자")
        self.assertEqual(res.context["book"].pk, 2)
        self.assertEqual(res.context["page"].paginator.count, 4)
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
        self.assertContains(self.client.get("/threads/7/"), f'href="{book.get_absolute_url()}"')
        # 쓰레드가 5개를 넘어 페이지가 나뉘어도 페이지 링크에 제목이 유지된다
        writer = User.objects.create_user("pager")
        for i in range(2):
            Thread.objects.create(book=book, user=writer, title=f"추가 {i}", body="본문")
        self.assertContains(self.client.get(book.get_absolute_url()), "?title=%EC%B1%84%EC%8B%9D%EC%A3%BC%EC%9D%98%EC%9E%90&amp;page=2")

    def test_book_detail_stats_and_sections(self):
        res = self.client.get("/books/?title=채식주의자")
        self.assertEqual(res.context["stats"], {"archived": 0, "threads": 4, "likes": 128 + 94 + 71 + 58})
        self.assertEqual([t.num_likes for t in res.context["popular_threads"]], [128, 94, 71])
        similar = res.context["similar_books"]
        self.assertEqual(len(similar), 6)
        self.assertNotIn(2, [b.pk for b in similar])
        self.assertEqual([b.genre for b in similar[:3]], ["철학"] * 3)  # 같은 장르 먼저
        self.assertContains(res, "이 책의 인기 쓰레드")
        # 쓰레드가 없는 책은 첫 쓰레드 안내
        self.assertContains(self.client.get("/books/?title=Bauhaus"), "아직 이 책의 쓰레드가 없어요")


class ActionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("load_sample_data", verbosity=0)
        cls.user = User.objects.create_user("reader", password="thread-pass-123", nickname="독자")
        cls.other = User.objects.create_user("other", password="thread-pass-123", nickname="다른독자")

    def test_anonymous_actions_redirect_to_login(self):
        res = self.client.post(reverse("books:archive", args=[2]))
        self.assertRedirects(res, "/accounts/login/?next=%2Fbooks%2F%3Ftitle%3D%25EC%25B1%2584%25EC%258B%259D%25EC%25A3%25BC%25EC%259D%2598%25EC%259E%2590",
                             fetch_redirect_response=False)
        res = self.client.post(reverse("threads:like", args=[1]))
        self.assertRedirects(res, "/accounts/login/?next=%2Fthreads%2F1%2F", fetch_redirect_response=False)
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
        self.client.force_login(self.user)
        self.client.post(reverse("threads:like", args=[1]))
        self.client.force_login(self.other)
        self.client.post(reverse("threads:like", args=[1]))
        t = Thread.objects.with_likes(self.other).get(pk=1)
        self.assertEqual(t.num_likes, 128 + 2)
        self.assertTrue(t.is_liked)
        # 마이 페이지 '좋아요한 쓰레드'에서도 전체 좋아요 수가 나와야 함
        liked = self.client.get("/mypage/").context["liked"]
        self.assertEqual(liked[0].num_likes, 130)
        self.client.post(reverse("threads:like", args=[1]))
        self.assertEqual(Thread.objects.with_likes().get(pk=1).num_likes, 129)

    def test_write_and_delete_thread(self):
        self.client.force_login(self.user)
        self.assertContains(self.client.get(reverse("threads:write") + "?book=3"), 'value="3" selected')
        res = self.client.post(
            reverse("threads:write"),
            {"book": 3, "image": "", "title": "  새 쓰레드  ", "body": "본문입니다"},
        )
        thread = Thread.objects.get(title="새 쓰레드")
        self.assertRedirects(res, reverse("threads:detail", args=[thread.pk]))
        self.assertEqual(thread.image_path, Book.objects.get(pk=3).cover)
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
