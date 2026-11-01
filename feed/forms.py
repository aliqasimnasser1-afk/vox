from django import forms

from .media import classify
from .models import MAX_LEN


class PostForm(forms.Form):
    content = forms.CharField(
        max_length=MAX_LEN, strip=True, required=False,
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "وش الجديد؟", "maxlength": MAX_LEN}),
    )
    media = forms.FileField(required=False, widget=forms.FileInput(attrs={"accept": "image/*,video/mp4,video/webm,video/quicktime"}))

    def clean_media(self):
        f = self.cleaned_data.get("media")
        if not f:
            return None
        return classify(f)  # (kind, file)

    def clean(self):
        data = super().clean()
        if not data.get("content") and not data.get("media") and not self.errors:
            raise forms.ValidationError("اكتب شيئاً أو أرفق صورة أو فيديو.")
        return data
