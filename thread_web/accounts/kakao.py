"""카카오 로그인 REST API 호출 (표준 라이브러리 urllib 사용)

REST API 키와 클라이언트 시크릿은 서버에서만 사용하고 브라우저로 내보내지 않는다.
"""
import json
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings

AUTHORIZE_URL = "https://kauth.kakao.com/oauth/authorize"
TOKEN_URL = "https://kauth.kakao.com/oauth/token"
USER_ME_URL = "https://kapi.kakao.com/v2/user/me"
LOGOUT_URL = "https://kapi.kakao.com/v1/user/logout"


class KakaoError(Exception):
    pass


def _request(url, data=None, token=None, method="POST"):
    headers = {"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = urllib.parse.urlencode(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            return json.load(res)
    except urllib.error.HTTPError as e:
        raise KakaoError(e.read().decode(errors="replace")) from e
    except (urllib.error.URLError, ValueError) as e:
        raise KakaoError(str(e)) from e


def authorize_url(redirect_uri, state):
    params = {
        "response_type": "code",
        "client_id": settings.KAKAO_REST_API_KEY,
        "redirect_uri": redirect_uri,
        "state": state,
        # 브라우저에 카카오 로그인이 남아 있어도 매번 카카오 계정을 다시 입력받는다 (다른 계정으로 전환 가능)
        "prompt": "login",
    }
    return f"{AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"


def fetch_profile(code, redirect_uri):
    """인가 코드로 토큰을 받아 회원 정보를 조회하고, 토큰은 바로 만료시킨다."""
    data = {
        "grant_type": "authorization_code",
        "client_id": settings.KAKAO_REST_API_KEY,
        "redirect_uri": redirect_uri,
        "code": code,
    }
    if settings.KAKAO_CLIENT_SECRET:
        data["client_secret"] = settings.KAKAO_CLIENT_SECRET
    token = _request(TOKEN_URL, data).get("access_token")
    if not token:
        raise KakaoError("access_token 없음")
    me = _request(USER_ME_URL, token=token, method="GET")
    try:
        _request(LOGOUT_URL, token=token)  # 서비스는 카카오 API를 더 쓰지 않으므로 토큰 만료
    except KakaoError:
        pass

    profile = me.get("kakao_account", {}).get("profile", {})
    return {
        "id": me["id"],
        "nickname": profile.get("nickname", ""),
        "image": profile.get("thumbnail_image_url", ""),
    }
