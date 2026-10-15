import json
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from books.models import Author, Book
from threads.models import Thread

DATA_FILE = Path(__file__).resolve().parents[2] / "fixtures" / "sample_data.json"


class Command(BaseCommand):
    help = "fixtures/sample_data.json 의 도서·작가·쓰레드 샘플 데이터를 DB에 넣습니다."

    @transaction.atomic
    def handle(self, *args, **options):
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        User = get_user_model()

        for a in data["authors"]:
            Author.objects.update_or_create(name=a["name"], defaults={"bio": a["bio"]})

        for b in data["books"]:
            book_id = b.pop("id")
            Book.objects.update_or_create(id=book_id, defaults=b)

        for t in data["threads"]:
            # 샘플 작성자는 로그인할 수 없는 회원으로 만든다 (비밀번호 없음)
            author, created = User.objects.get_or_create(
                username=f"sample_{t['author']}", defaults={"nickname": t["author"]}
            )
            if created:
                author.set_unusable_password()
                author.save()
            Thread.objects.update_or_create(
                id=t["id"],
                defaults={
                    "book_id": t["book"],
                    "user": author,
                    "title": t["title"],
                    "body": t["body"],
                    "image": t["image"],
                    "seed_likes": t["seed_likes"],
                },
            )

        if options["verbosity"]:
            self.stdout.write(
                self.style.SUCCESS(
                    f"샘플 데이터: 도서 {len(data['books'])}권, 작가 {len(data['authors'])}명, 쓰레드 {len(data['threads'])}개"
                )
            )
