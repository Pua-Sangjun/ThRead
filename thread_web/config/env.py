"""설정 값 읽기: 서버 환경 변수 → .env 파일 순서로 찾는다. 외부 패키지 없이 사용한다."""
import os


def read_env(path):
    """KEY = value 형식의 .env 파일을 dict 로 읽는다 (# 주석 허용)."""
    env = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip("'\"")
    return env


class Env:
    def __init__(self, env_file):
        self.file_values = read_env(env_file)

    def str(self, key, default=""):
        # 배포 서버(Render 등)는 환경 변수로, 로컬은 .env 로 값을 준다
        return os.environ.get(key) or self.file_values.get(key) or default

    def bool(self, key, default=False):
        value = self.str(key)
        if not value:
            return default
        return value.lower() in ("1", "true", "yes", "on")

    def list(self, key):
        return [v.strip() for v in self.str(key).split(",") if v.strip()]
