from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import User


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "아이디"

    error_messages = {
        "invalid_login": "아이디 또는 비밀번호가 올바르지 않습니다.",
        "inactive": "사용할 수 없는 계정입니다.",
    }


class SignupForm(UserCreationForm):
    nickname = forms.CharField(
        label="닉네임",
        min_length=2,
        max_length=20,
        help_text="2~20자, 다른 독자에게 표시되는 이름이에요.",
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "nickname")
        labels = {"username": "아이디"}
