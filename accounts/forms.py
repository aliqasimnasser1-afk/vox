import re
import secrets

from django import forms
from django.contrib.auth import authenticate, get_user_model, password_validation
from django.core.exceptions import ValidationError

from .models import Profile

User = get_user_model()


class SignupForm(forms.Form):
    name = forms.CharField(label="الاسم", min_length=2, max_length=40)
    email = forms.EmailField(label="البريد الإلكتروني")
    password = forms.CharField(label="كلمة المرور", widget=forms.PasswordInput)

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("هذا البريد مسجّل مسبقاً.")
        return email

    def clean(self):
        data = super().clean()
        if data.get("password"):
            probe = User(email=data.get("email", ""), first_name=data.get("name", ""))
            password_validation.validate_password(data["password"], probe)
        return data

    def _unique_username(self, email):
        base = re.sub(r"[^a-z0-9_]", "", email.split("@")[0].lower())[:14] or "user"
        if len(base) < 3:
            base = f"user{base}"
        username = base
        while User.objects.filter(username=username).exists():
            username = f"{base}{secrets.token_hex(2)}"
        return username

    def save(self):
        d = self.cleaned_data
        return User.objects.create_user(
            username=self._unique_username(d["email"]),
            email=d["email"],
            password=d["password"],
            first_name=d["name"],
        )


class LoginForm(forms.Form):
    email = forms.EmailField(label="البريد الإلكتروني")
    password = forms.CharField(label="كلمة المرور", widget=forms.PasswordInput)

    def __init__(self, *args, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request
        self.user = None

    def clean(self):
        data = super().clean()
        if data.get("email") and data.get("password"):
            self.user = authenticate(self.request, email=data["email"], password=data["password"])
            if self.user is None:
                raise ValidationError("البريد أو كلمة المرور غير صحيحة.")
        return data


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["display_name", "bio"]
        widgets = {"bio": forms.Textarea(attrs={"rows": 3})}
