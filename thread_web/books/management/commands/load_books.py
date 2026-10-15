import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from books.models import Author, Book

DATA_FILE = Path(__file__).resolve().parents[2] / "fixtures" / "books.json"


class Command(BaseCommand):
    help = "fixtures/books.json 의 도서·작가 정보를 DB에 넣거나 갱신합니다. (배포할 때마다 실행해도 안전)"

    @transaction.atomic
    def handle(self, *args, **options):
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))

        for a in data["authors"]:
            Author.objects.update_or_create(name=a["name"], defaults={"bio": a["bio"]})

        for b in data["books"]:
            book_id = b.pop("id")
            Book.objects.update_or_create(id=book_id, defaults=b)

        if options["verbosity"]:
            self.stdout.write(self.style.SUCCESS(f"도서 {len(data['books'])}권, 작가 {len(data['authors'])}명"))
