from django import forms
from django.contrib.auth import authenticate, get_user_model, password_validation
from django.core.exceptions import ValidationError

from .models import Profile
from .validators import clean_username

User = get_user_model()
MAX_AVATAR = 2 * 1024 * 1024


class SignupForm(forms.Form):
    name = forms.CharField(label="الاسم", min_length=2, max_length=40)
    username = forms.CharField(label="اسم المستخدم", max_length=20,
                               help_text="يظهر للجميع بدل بريدك. إنجليزية وأرقام و _ فقط.",
                               widget=forms.TextInput(attrs={"dir": "ltr", "autocomplete": "username", "placeholder": "ali_2026"}))
    email = forms.EmailField(label="البريد الإلكتروني", help_text="خاص بك، لا يظهر لأحد.")
    password = forms.CharField(label="كلمة المرور", widget=forms.PasswordInput)

    def clean_username(self):
        return clean_username(self.cleaned_data["username"])

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

    def save(self):
        d = self.cleaned_data
        return User.objects.create_user(
            username=d["username"],
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
    username = forms.CharField(label="اسم المستخدم", max_length=20,
                               widget=forms.TextInput(attrs={"dir": "ltr", "autocomplete": "off"}))
    remove_avatar = forms.BooleanField(label="حذف الصورة الحالية", required=False)

    class Meta:
        model = Profile
        fields = ["display_name", "bio", "location", "website", "avatar"]
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 3}),
            "avatar": forms.FileInput(attrs={"accept": "image/*"}),
            "website": forms.URLInput(attrs={"dir": "ltr", "placeholder": "https://"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].initial = self.instance.user.username
        self.order_fields(["avatar", "remove_avatar", "display_name", "username", "bio", "location", "website"])

    def clean_username(self):
        value = self.cleaned_data["username"].strip().lstrip("@").lower()
        if value == self.instance.user.username.lower():
            return self.instance.user.username  # unchanged: never block saving other fields
        return clean_username(value, exclude_pk=self.instance.user_id)

    def clean_avatar(self):
        f = self.cleaned_data.get("avatar")
        if f and hasattr(f, "size") and f.size > MAX_AVATAR:
            raise ValidationError("حجم الصورة أكبر من 2 ميجابايت.")
        return f

    def save(self, commit=True):
        profile = super().save(commit=False)
        old = Profile.objects.filter(pk=profile.pk).first()
        old_avatar = old.avatar if old and old.avatar else None
        if self.cleaned_data.get("remove_avatar") and not self.files.get("avatar"):
            profile.avatar = ""
        if commit:
            profile.save()
            user = profile.user
            if user.username != self.cleaned_data["username"]:
                user.username = self.cleaned_data["username"]
                user.save(update_fields=["username"])
            if old_avatar and old_avatar.name != (profile.avatar.name if profile.avatar else ""):
                old_avatar.storage.delete(old_avatar.name)  # drop the replaced file
        return profile
