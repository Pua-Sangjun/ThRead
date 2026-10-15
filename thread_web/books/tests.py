from unittest import mock

from django.core.cache import cache
from django.test import TestCase, override_settings

from accounts.models import User
from threads.models import Thread

from . import kakao
from .models import Book

VEGETARIAN = {
    "title": "채식주의자",
    "authors": ["한강"],
    "publisher": "창비",
    "datetime": "2022-03-28T00:00:00.000+09:00",
    "isbn": "8936434594 9788936434595",
    "thumbnail": "https://search1.kakaocdn.net/thumb/R120x174.q85/?fname=vegetarian",
    "contents": "어느 날 꿈을 꾼 뒤로 고기를 먹지 않기로 결심한 영혜...",
}
BOY = {**VEGETARIAN, "title": "소년이 온다", "isbn": "8936434128 9788936434120", "thumbnail": "https://k/boy"}
NO_ISBN = {**VEGETARIAN, "title": "ISBN 없는 책", "isbn": ""}


def kakao_response(docs, total=None, is_end=True):
    return {"documents": docs, "meta": {"pageable_count": len(docs) if total is None else total, "is_end": is_end}}


@override_settings(KAKAO_REST_API_KEY="dummy")
class KakaoModuleTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_pick_isbn_prefers_13_digits(self):
        self.assertEqual(kakao.pick_isbn("8936434594 9788936434595"), "9788936434595")
        self.assertEqual(kakao.pick_isbn(" 9788936434595"), "9788936434595")
        self.assertEqual(kakao.pick_isbn("8936434594"), "8936434594")
        self.assertEqual(kakao.pick_isbn(""), "")

    def test_to_book_fields(self):
        f = kakao.to_book_fields(VEGETARIAN)
        self.assertEqual(f["isbn"], "9788936434595")
        self.assertEqual((f["author"], f["publisher"], f["year"]), ("한강", "창비", 2022))

    @mock.patch("books.kakao._get", return_value=kakao_response([VEGETARIAN, NO_ISBN], total=99, is_end=False))
    def test_search_drops_results_without_isbn(self, _get):
        books, total, is_end = kakao.search("한강", page=2)
        self.assertEqual([b["title"] for b in books], ["채식주의자"])
        self.assertEqual((total, is_end), (99, False))
        _get.assert_called_once_with({"query": "한강", "page": 2, "size": kakao.PAGE_SIZE})

    def test_requests_are_cached(self):
        fake = mock.MagicMock()
        fake.__enter__.return_value.read.return_value = b'{"documents": [], "meta": {}}'
        with mock.patch("urllib.request.urlopen", return_value=fake) as urlopen, mock.patch("json.load", return_value={"documents": [], "meta": {}}):
            kakao.search("캐시")
            kakao.search("캐시")
        self.assertEqual(urlopen.call_count, 1)

    @override_settings(KAKAO_REST_API_KEY="")
    def test_missing_key_raises(self):
        with self.assertRaises(kakao.KakaoBookError):
            kakao.search("한강")


@override_settings(KAKAO_REST_API_KEY="dummy")
class SearchPageTests(TestCase):
    def setUp(self):
        cache.clear()

    @mock.patch("books.kakao._get", return_value=kakao_response([VEGETARIAN, BOY], total=60, is_end=False))
    def test_search_shows_kakao_results_without_saving(self, _get):
        res = self.client.get("/books/search/", {"q": "한강"})
        self.assertContains(res, "'한강' 검색 결과 60권")
        self.assertContains(res, 'href="/books/?isbn=9788936434595"')
        self.assertContains(res, "다음")
        self.assertEqual(Book.objects.count(), 0)  # 검색만으로는 저장하지 않음

    @mock.patch("books.kakao._get", side_effect=kakao.KakaoBookError("down"))
    def test_search_error_message(self, _get):
        self.assertContains(self.client.get("/books/search/", {"q": "한강"}), "지금은 도서 검색을 할 수 없어요")

    def test_without_query_shows_registered_books(self):
        Book.objects.create(isbn="9788936434595", title="채식주의자")
        res = self.client.get("/books/search/")
        self.assertContains(res, "ThRead 독자들이 살펴본 책")
        self.assertContains(res, "채식주의자")


@override_settings(KAKAO_REST_API_KEY="dummy")
class DetailTests(TestCase):
    def setUp(self):
        cache.clear()

    @mock.patch("books.kakao._get")
    def test_first_visit_saves_book_from_kakao(self, _get):
        _get.side_effect = lambda params: kakao_response([VEGETARIAN] if params.get("target") == "isbn" else [BOY, VEGETARIAN])
        res = self.client.get("/books/", {"isbn": "9788936434595"})
        self.assertEqual(res.status_code, 200)
        book = Book.objects.get(isbn="9788936434595")
        self.assertEqual((book.title, book.author, book.publisher), ("채식주의자", "한강", "창비"))
        # 이 작가의 다른 책: 같은 책은 빼고 보여준다
        self.assertEqual([b.title for b in res.context["author_books"]], ["소년이 온다"])
        self.assertContains(res, "한강의 다른 책")
        # 두 번째 방문은 DB 에서 (카카오 ISBN 조회 없음)
        _get.reset_mock()
        self.client.get("/books/", {"isbn": "9788936434595"})
        self.assertNotIn("isbn", [c.args[0].get("target") for c in _get.call_args_list])

    @mock.patch("books.kakao._get", return_value=kakao_response([VEGETARIAN]))
    def test_isbn10_redirects_to_isbn13(self, _get):
        res = self.client.get("/books/", {"isbn": "8936434594"})
        self.assertRedirects(res, "/books/?isbn=9788936434595", status_code=301, fetch_redirect_response=False)
        self.assertEqual(Book.objects.count(), 1)

    @mock.patch("books.kakao._get", return_value=kakao_response([]))
    def test_unknown_isbn_is_404(self, _get):
        self.assertEqual(self.client.get("/books/", {"isbn": "0000000000000"}).status_code, 404)

    @mock.patch("books.kakao._get", return_value=kakao_response([]))
    def test_old_urls_redirect(self, _get):
        book = Book.objects.create(isbn="9788936434595", title="채식주의자")
        self.assertRedirects(self.client.get(f"/books/{book.pk}/"), book.get_absolute_url(), status_code=301,
                             fetch_redirect_response=False)
        self.assertRedirects(self.client.get("/books/", {"title": "채식주의자"}), book.get_absolute_url(), status_code=301,
                             fetch_redirect_response=False)
        self.assertRedirects(self.client.get("/books/"), "/books/search/")

    def test_cover_url_falls_back_to_default(self):
        self.assertEqual(Book(isbn="1", title="t").cover_url, "/static/covers/no-cover.webp")
        self.assertEqual(Book(isbn="1", title="t", cover="https://k/c").cover_url, "https://k/c")


@override_settings(KAKAO_REST_API_KEY="")
class MainPageTests(TestCase):
    def test_popular_books_by_reader_activity(self):
        users = [User.objects.create_user(f"u{i}") for i in range(2)]
        a = Book.objects.create(isbn="1", title="많이 담은 책")
        b = Book.objects.create(isbn="2", title="쓰레드 있는 책")
        Book.objects.create(isbn="3", title="아무도 안 본 책")
        a.archived_by.add(*users)
        Thread.objects.create(book=b, user=users[0], title="t", body="b")
        res = self.client.get("/")
        titles = [bk.title for slide in res.context["book_slides"] for bk in slide]
        self.assertEqual(titles, ["많이 담은 책", "쓰레드 있는 책"])

    def test_empty_site(self):
        res = self.client.get("/")
        self.assertContains(res, "아직 담은 책이 없어요")
        self.assertContains(res, "아직 쓰레드가 없습니다.")
        self.assertContains(res, 'href="/books/search/?q=%EC%97%AC%ED%96%89"')  # 주제 '여행' → 카카오 검색
        self.assertNotContains(res, "AI 추천")
