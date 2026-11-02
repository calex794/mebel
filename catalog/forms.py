import re

from django import forms


class LeadForm(forms.Form):
    name = forms.CharField(
        label="Как к вам обращаться",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Имя (необязательно)", "autocomplete": "name"}),
    )
    phone = forms.CharField(
        label="Телефон",
        max_length=40,
        widget=forms.TextInput(attrs={
            "placeholder": "+7 (999) 123-45-67",
            "autocomplete": "tel",
            "inputmode": "tel",
            "required": "required",
        }),
    )
    message = forms.CharField(
        label="Что хотите заказать",
        max_length=1200,
        required=False,
        widget=forms.Textarea(attrs={
            "rows": 3,
            "placeholder": "Например, кухня или шкаф (необязательно)",
        }),
    )
    consent = forms.BooleanField(
        label="Согласен(на) на обработку персональных данных для связи по заявке",
        required=True,
    )
    # Honeypot: ordinary users never see this field.
    website = forms.CharField(required=False, widget=forms.HiddenInput)

    def clean_phone(self):
        phone = self.cleaned_data["phone"].strip()
        if not re.fullmatch(r"[+0-9()\s\-]{10,40}", phone):
            raise forms.ValidationError("Введите корректный номер телефона.")
        digits = re.sub(r"\D", "", phone)
        if not 10 <= len(digits) <= 15:
            raise forms.ValidationError("Введите корректный номер телефона.")
        return phone

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise forms.ValidationError("Неверная заявка.")
        return ""
