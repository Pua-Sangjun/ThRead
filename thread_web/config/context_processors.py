from django.conf import settings


def kakao(request):
    """모든 템플릿에서 카카오 설정 여부를 쓸 수 있게 한다. (시크릿 값은 넘기지 않음)"""
    return {
        "KAKAO_APP_KEY": settings.KAKAO_APP_KEY,
        "KAKAO_LOGIN_ENABLED": bool(settings.KAKAO_REST_API_KEY),
    }


def navigation(request):
    """네비게이션 메뉴 강조용 현재 페이지 정보. (404 처럼 주소가 매칭되지 않으면 빈 값)"""
    match = request.resolver_match
    return {
        "nav_namespace": match.namespace if match else "",
        "nav_name": match.url_name if match else "",
    }
