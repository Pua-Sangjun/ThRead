from django import forms

from books.models import Book

from .models import THREAD_IMAGES, Thread


class ThreadForm(forms.ModelForm):
    # 빈 값 = 선택한 도서의 표지
    image = forms.ChoiceField(
        label="대표 이미지",
        choices=[("", "도서 표지")] + [(img, f"이미지 {i}") for i, img in enumerate(THREAD_IMAGES, 1)],
        required=False,
        widget=forms.RadioSelect,
    )

    class Meta:
        model = Thread
        fields = ("book", "image", "title", "body")
        widgets = {
            "book": forms.Select(attrs={"class": "form-select"}),
            "title": forms.TextInput(attrs={"class": "form-control", "maxlength": 60}),
            "body": forms.Textarea(attrs={"class": "form-control", "rows": 8}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["book"].queryset = Book.objects.all()
        self.fields["book"].empty_label = None

    def clean_title(self):
        return self.cleaned_data["title"].strip()

    def clean_body(self):
        body = self.cleaned_data["body"].strip()
        if not body:
            raise forms.ValidationError("내용을 입력해 주세요.")
        return body
