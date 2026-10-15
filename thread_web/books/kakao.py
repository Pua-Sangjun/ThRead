"""카카오 책 검색 API (https://developers.kakao.com/docs/latest/ko/daum-search/dev-guide#search-book)

REST API 키는 서버에서만 쓰고, 같은 요청은 잠시 캐시해 호출 수를 줄인다.
"""
import hashlib
import json
import logging
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

SEARCH_URL = "https://dapi.kakao.com/v3/search/book"
CACHE_SECONDS = 60 * 10
PAGE_SIZE = 24
MAX_PAGE = 50  # 카카오 책 검색이 허용하는 최대 페이지


class KakaoBookError(Exception):
    pass


def _get(params):
    if not settings.KAKAO_REST_API_KEY:
        raise KakaoBookError("KAKAO_REST_API_KEY 가 설정되지 않았습니다.")
    key = "kakao-book:" + hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()
    data = cache.get(key)
    if data is None:
        req = urllib.request.Request(
            f"{SEARCH_URL}?{urllib.parse.urlencode(params)}",
            headers={"Authorization": f"KakaoAK {settings.KAKAO_REST_API_KEY}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as res:
                data = json.load(res)
        except (urllib.error.URLError, ValueError) as e:
            logger.warning("카카오 책 검색 실패: %s", e)
            raise KakaoBookError(str(e)) from e
        cache.set(key, data, CACHE_SECONDS)
    return data


def pick_isbn(raw):
    """카카오는 'ISBN10 ISBN13' 처럼 공백으로 이어서 준다. 13자리를 우선 쓴다."""
    parts = [p for p in (raw or "").split() if p]
    return next((p for p in parts if len(p) == 13), parts[0] if parts else "")


def to_book_fields(doc):
    """카카오 검색 결과 한 건 → Book 필드"""
    year = doc.get("datetime", "")[:4]
    return {
        "isbn": pick_isbn(doc.get("isbn")),
        "title": doc.get("title", "").strip(),
        "author": ", ".join(doc.get("authors") or []),
        "publisher": doc.get("publisher", ""),
        "year": int(year) if year.isdigit() else None,
        "cover": doc.get("thumbnail", ""),
        "description": doc.get("contents", ""),
    }


def search(query, page=1, target=None, size=PAGE_SIZE):
    """검색어로 책을 찾는다. → (Book 필드 dict 목록, 전체 건수, 마지막 페이지 여부)

    ISBN 이 없는 결과는 상세 페이지를 만들 수 없으므로 뺀다.
    """
    params = {"query": query, "page": max(1, min(page, MAX_PAGE)), "size": size}
    if target:
        params["target"] = target
    data = _get(params)
    books = [to_book_fields(d) for d in data.get("documents", [])]
    meta = data.get("meta", {})
    return [b for b in books if b["isbn"]], meta.get("pageable_count", 0), meta.get("is_end", True)


def find_by_isbn(isbn):
    """ISBN(10자리 또는 13자리)으로 한 권을 찾는다. 없으면 None"""
    data = _get({"query": isbn, "target": "isbn", "size": 5})
    for doc in data.get("documents", []):
        if isbn in (doc.get("isbn") or "").split():
            return to_book_fields(doc)
    return None
