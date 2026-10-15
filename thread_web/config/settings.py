"""
ThRead Django 설정

값은 서버 환경 변수 → pjt_03/.env 순서로 읽는다. (config/env.py)
- 로컬 개발: 아무것도 없어도 DEBUG=True, SQLite 로 실행된다.
- 배포: DJANGO_DEBUG=False 와 DJANGO_SECRET_KEY, DJANGO_ALLOWED_HOSTS, DATABASE_URL 을 환경 변수로 준다.

https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/
"""

import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

from .env import Env

BASE_DIR = Path(__file__).resolve().parent.parent
env = Env(BASE_DIR.parent / ".env")  # 프로젝트 루트(pjt_03)의 .env (.gitignore 대상)


# ========== 기본 / 보안 ==========
DEBUG = env.bool("DJANGO_DEBUG", default=True)

SECRET_KEY = env.str("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured("배포 환경에서는 DJANGO_SECRET_KEY 환경 변수가 필요합니다.")
    SECRET_KEY = "django-insecure-local-development-only"

ALLOWED_HOSTS = ["localhost", "127.0.0.1", *env.list("DJANGO_ALLOWED_HOSTS")]
# Render 는 서비스 주소(xxx.onrender.com)를 RENDER_EXTERNAL_HOSTNAME 으로 알려준다
if os.environ.get("RENDER_EXTERNAL_HOSTNAME"):
    ALLOWED_HOSTS.append(os.environ["RENDER_EXTERNAL_HOSTNAME"])
CSRF_TRUSTED_ORIGINS = [f"https://{host}" for host in ALLOWED_HOSTS if host not in ("localhost", "127.0.0.1")]

if not DEBUG:
    # 배포 서버는 HTTPS 를 프록시(로드밸런서)가 처리하고 앱에는 HTTP 로 넘겨준다
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # HSTS: 처음엔 짧게(1시간) 두고, 문제가 없으면 DJANGO_HSTS_SECONDS 로 늘린다 (예: 31536000)
    SECURE_HSTS_SECONDS = int(env.str("DJANGO_HSTS_SECONDS", "3600"))

# HSTS 하위 도메인 포함·preload 는 도메인 전체에 영향을 주므로 끈다.
# (xxx.onrender.com 처럼 남의 도메인을 쓰는 동안은 켤 수 없고, 직접 산 도메인을 쓸 때 검토)
SILENCED_SYSTEM_CHECKS = ["security.W005", "security.W021"]


# ========== 앱 ==========
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "books",
    "threads",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # 정적 파일 서빙 (Nginx 없이)
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "config.context_processors.kakao",
                "config.context_processors.navigation",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# ========== DB ==========
# DATABASE_URL 이 있으면 그 DB(PostgreSQL 등), 없으면 로컬 SQLite
DATABASES = {
    "default": dj_database_url.parse(
        env.str("DATABASE_URL", f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
        conn_max_age=600,
        conn_health_checks=True,
    )
}


# ========== 비밀번호 검사 ==========
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# ========== 언어 / 시간 ==========
LANGUAGE_CODE = "ko-kr"
TIME_ZONE = "Asia/Seoul"
USE_I18N = True
USE_TZ = True


# ========== 정적 파일 ==========
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"  # collectstatic 결과 (배포용, .gitignore 대상)
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    # 배포 시 파일명에 해시를 붙이고 압축해 브라우저 캐시가 잘 되게 한다
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        if DEBUG
        else "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ========== 로그 (배포 서버 콘솔에서 확인) ==========
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}


# ========== 회원 / 로그인 ==========
AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "books:main"
LOGOUT_REDIRECT_URL = "books:main"


# ========== 카카오 (Kakao Developers 앱 키) ==========
KAKAO_APP_KEY = env.str("KAKAO_APP_KEY")              # JavaScript 키: 카카오맵
KAKAO_REST_API_KEY = env.str("KAKAO_REST_API_KEY")    # REST API 키: 카카오 로그인
KAKAO_CLIENT_SECRET = env.str("KAKAO_CLIENT_SECRET")  # 클라이언트 시크릿: 카카오 로그인
# 카카오 콘솔 > 카카오 로그인 > Redirect URI 에 등록한 경로
KAKAO_REDIRECT_PATH = "/api/kakao/callback"
