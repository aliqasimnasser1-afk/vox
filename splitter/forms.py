import os
from pathlib import Path

from django import forms

ALLOWED = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}
# Per-host cap (MB). PythonAnywhere has a 512 MB disk, so its WSGI file lowers this.
MAX_BYTES = int(os.environ.get("MAX_VIDEO_MB", "2048")) * 1024 * 1024
MAX_PARTS = 300


class SplitForm(forms.Form):
    video = forms.FileField(label="الفيديو", widget=forms.FileInput(attrs={"accept": "video/*"}))
    amount = forms.IntegerField(label="طول كل جزء", min_value=1, max_value=86400, initial=30,
                                widget=forms.NumberInput(attrs={"inputmode": "numeric"}))
    unit = forms.ChoiceField(label="الوحدة", choices=[("s", "ثانية"), ("m", "دقيقة")], initial="s")
    mode = forms.ChoiceField(label="طريقة التقسيم", choices=[("fast", "سريع جداً"), ("precise", "دقيق")],
                             initial="fast", widget=forms.RadioSelect)

    def clean_video(self):
        f = self.cleaned_data["video"]
        if Path(f.name).suffix.lower() not in ALLOWED:
            raise forms.ValidationError("صيغة غير مدعومة. المسموح: " + "، ".join(sorted(e[1:] for e in ALLOWED)))
        if f.size > MAX_BYTES:
            raise forms.ValidationError(f"حجم الفيديو أكبر من {MAX_BYTES // (1024 * 1024)} ميجابايت.")
        return f

    @property
    def segment_seconds(self):
        d = self.cleaned_data
        return d["amount"] * (60 if d["unit"] == "m" else 1)


class SplitParamsForm(forms.Form):
    """The split settings alone, used when the video itself arrived in chunks."""
    amount = SplitForm.base_fields["amount"]
    unit = SplitForm.base_fields["unit"]
    mode = SplitForm.base_fields["mode"]

    @property
    def segment_seconds(self):
        d = self.cleaned_data
        return d["amount"] * (60 if d["unit"] == "m" else 1)
