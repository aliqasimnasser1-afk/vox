from django import forms

from .models import MAX_LEN


class PostForm(forms.Form):
    content = forms.CharField(
        max_length=MAX_LEN,
        strip=True,
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "وش الجديد؟", "maxlength": MAX_LEN}),
    )
