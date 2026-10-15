#!/usr/bin/env bash
# Render 빌드 스크립트: 패키지 설치 → 정적 파일 모으기 → DB 마이그레이션
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate --no-input

# 관리자 계정: DJANGO_SUPERUSER_USERNAME / DJANGO_SUPERUSER_PASSWORD 환경 변수가 있을 때만 (이미 있으면 건너뜀)
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  python manage.py createsuperuser --no-input || true
fi
