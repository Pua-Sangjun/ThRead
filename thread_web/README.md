# ThRead

> AI 기반 도서 분석 및 창작 지원 통합 솔루션 서비스.
> 도서를 검색하고 담고, 책마다 감상(쓰레드)을 나누는 Django 웹 서비스입니다.
> 회원·담기·쓰레드·좋아요는 DB에 저장되고, 카카오 로그인과 카카오맵을 지원합니다.

## 1. 실행 방법

```bash
cd thread_web
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py load_books   # 도서 15권 · 작가 정보
python manage.py runserver 5500
```

브라우저에서 `http://localhost:5500` 으로 접속합니다.
관리자 페이지(`/admin/`)를 쓰려면 `python manage.py createsuperuser`로 관리자 계정을 만드세요.

> 포트를 **5500**으로 실행하는 이유: 카카오 콘솔에 등록한 사이트 도메인·Redirect URI(`http://localhost:5500/api/kakao/callback`)와
> 맞추기 위해서입니다. 다른 포트를 쓰려면 카카오 콘솔에도 그 주소를 추가하세요.

### 카카오 콘솔 설정

| 메뉴 | 값 |
| --- | --- |
| 플랫폼 > Web > 사이트 도메인 | `http://localhost:5500` |
| 카카오 로그인 > Redirect URI | `http://localhost:5500/api/kakao/callback` |
| 카카오 로그인 > 동의항목 | 닉네임(필수), 프로필 사진(선택) |

### 환경 변수 (`pjt_03/.env`, 선택)

| 키 | 용도 | 없으면 |
| --- | --- | --- |
| `KAKAO_APP_KEY` | JavaScript 키 · 도서 상세 카카오맵 | 지도 대신 "카카오맵에서 보기" 안내 |
| `KAKAO_REST_API_KEY` | REST API 키 · 카카오 로그인 | 카카오 로그인 버튼 숨김 (아이디 로그인만) |
| `KAKAO_CLIENT_SECRET` | 클라이언트 시크릿 · 카카오 로그인 | 시크릿 없이 토큰 요청 |
| `DJANGO_SECRET_KEY` | Django 비밀 키 | 개발용 키 사용 (배포 모드에서는 실행 거부) |
| `DJANGO_DEBUG` | `False`면 배포 모드 (HTTPS 강제, 보안 쿠키, 오류 화면 숨김) | `True` |
| `DJANGO_ALLOWED_HOSTS` | 접속 허용 도메인 (쉼표로 구분) | localhost만 (Render 주소는 자동 추가) |
| `DATABASE_URL` | PostgreSQL 등 DB 주소 | `db.sqlite3` |

값은 **서버 환경 변수 → `.env`** 순서로 읽습니다.

## 2. 구조

```
thread_web/
├── config/                 # settings, urls, .env 읽기, 템플릿 공통 변수(카카오)
├── accounts/               # 회원(커스텀 User), 로그인·회원가입·로그아웃, 카카오 로그인, 마이 페이지
│   └── kakao.py            # 카카오 OAuth REST API 호출 (urllib)
├── books/                  # 도서·작가 모델, 메인, 검색, 상세(카카오맵), 담기
│   ├── fixtures/books.json            # 도서 15권 · 작가 정보
│   └── management/commands/load_books.py
├── threads/                # 쓰레드 모델, 목록·상세·작성·삭제, 좋아요
├── templates/              # base.html + 공통 조각(partials) + 앱별 페이지
└── static/                 # 이미지·폰트, 공통·페이지별 CSS
```

### 모델

| 모델 | 주요 필드 |
| --- | --- |
| `accounts.User` | `AbstractUser` + `nickname`, `kakao_id`(카카오 회원번호, 고유), `profile_image` |
| `books.Book` | 제목·작가·출판사·연도·장르·표지·소개, `bestseller_rank`, `is_ai_pick`, `archived_by`(담은 회원, M:N) |
| `books.Author` | 작가 이름·소개 (도서 상세의 작가 소개) |
| `threads.Thread` | 도서(FK)·작성자(FK)·제목·내용·대표 이미지, `liked_by`(좋아요한 회원, M:N) |

좋아요 수는 실제 회원이 누른 수(`liked_by`)입니다. `Thread.objects.with_likes(user)`가 좋아요 수와 내 좋아요 여부를 한 번에 조회합니다.

### 주소

| 주소 | 화면 | 로그인 |
| --- | --- | --- |
| `/` | 메인 (베스트셀러, AI 추천, 장르, 인기 쓰레드) | |
| `/books/search/?q=&genre=` | 도서 검색 | |
| `/books/?title=책 제목` | 도서 상세 (카카오맵, 쓰레드 탭, 인기 쓰레드, 함께 보면 좋은 책). 예전 주소 `/books/<id>/`는 여기로 301 이동 | |
| `/books/<id>/archive/` | 담기 / 담기 취소 (POST) | 필요 |
| `/threads/?book=&sort=` | 쓰레드 목록 | |
| `/threads/<id>/` | 쓰레드 상세 | |
| `/threads/write/?book=` | 쓰레드 작성 | 필요 |
| `/threads/<id>/like/`, `/threads/<id>/delete/` | 좋아요 / 삭제 (POST, 삭제는 작성자만) | 필요 |
| `/mypage/` | 마이 페이지 (담은 도서, 내 쓰레드, 좋아요한 쓰레드) | 필요 |
| `/accounts/login/`, `/accounts/signup/` | 로그인, 회원가입 | |
| `/accounts/kakao/login/` → `/api/kakao/callback` | 카카오 로그인 | |
| `/accounts/logout/` (POST) | 로그아웃 | |

로그인이 필요한 동작을 하면 로그인 페이지로 이동했다가, 로그인 후 원래 페이지로 돌아옵니다.

## 3. 카카오 로그인 흐름

1. `/accounts/kakao/login/` — 무작위 `state`를 세션에 저장하고 카카오 인증 페이지로 이동
   (`prompt=login`: 브라우저에 카카오 로그인이 남아 있어도 매번 계정을 다시 입력받아 다른 카카오 계정으로 바꿔 로그인 가능)
2. `/api/kakao/callback` — `state`가 세션 값과 같은지 확인 (위조 요청 차단)
3. 인가 코드 + REST API 키 + 클라이언트 시크릿으로 토큰 발급 → 회원 정보(닉네임, 프로필 사진) 조회 → 토큰 즉시 만료
4. 카카오 회원번호로 회원을 찾거나 새로 만들고 Django 세션으로 로그인

REST API 키와 클라이언트 시크릿은 서버에서만 쓰고 브라우저로 보내지 않습니다.
카카오로 가입한 회원은 비밀번호가 없어 아이디 로그인은 할 수 없습니다.

## 4. 배포 (Render + Neon PostgreSQL)

| 파일 | 역할 |
| --- | --- |
| `../render.yaml` | Render Blueprint: 웹 서비스 설정 (빌드·실행 명령, 환경 변수) |
| `build.sh` | 패키지 설치 → `collectstatic` → `migrate` → 도서 정보(`load_books`) → (선택) 관리자 계정 생성 |
| `config/settings.py` | `DEBUG=False`일 때 HTTPS 리다이렉트·보안 쿠키·HSTS, WhiteNoise 정적 파일, `DATABASE_URL` |

DB는 Render 무료 PostgreSQL이 **30일 뒤 만료**되므로, 만료 없는 무료 PostgreSQL(예: [Neon](https://neon.tech))을 씁니다.
Render 무료 웹 서비스는 15분 동안 요청이 없으면 잠들고, 다음 접속 때 깨어나는 데 1분 정도 걸립니다.

1. **GitHub 저장소** — Render는 lab.ssafy.com 을 연결할 수 없으므로 GitHub에 저장소를 만들어 push 합니다.
2. **Neon** — 프로젝트를 **AWS Asia Pacific (Singapore)** 지역에 만들고, 연결 주소(`postgresql://...?sslmode=require`)를 복사합니다.
   **Connection pooling은 끈 주소**(호스트에 `-pooler`가 없는 주소)를 씁니다. Django가 DB 연결을 직접 유지하므로 풀러가 필요 없습니다.
3. **Render** — Dashboard > New > Blueprint > 저장소 선택. 입력 칸이 나오면 값을 넣습니다.
   - `DATABASE_URL`: Neon 연결 주소
   - `KAKAO_APP_KEY`, `KAKAO_REST_API_KEY`, `KAKAO_CLIENT_SECRET`: `.env`와 같은 값
   - `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_PASSWORD`: 관리자 계정 (선택)
   - `DJANGO_SECRET_KEY`는 Render가 자동으로 만듭니다.
4. **카카오 콘솔** — 배포 주소(예: `https://thread-xxxx.onrender.com`)를 추가합니다.
   - 플랫폼 > Web > 사이트 도메인: `https://thread-xxxx.onrender.com`
   - 카카오 로그인 > Redirect URI: `https://thread-xxxx.onrender.com/api/kakao/callback`

배포 설정 점검: `DJANGO_DEBUG=False DJANGO_SECRET_KEY=... python manage.py check --deploy`

## 5. 테스트

```bash
python manage.py test
```

페이지 렌더링, 회원가입·로그인, 담기, 쓰레드 작성·삭제 권한, 좋아요 수 계산, 입력값 이스케이프,
카카오 로그인(카카오 API 응답은 mock 처리: 성공, 취소, 위조된 state, 토큰 실패, 외부 next 차단), 매번 계정 입력(`prompt=login`)을 확인합니다.
