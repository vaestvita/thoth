from django import forms


class BitrixPortalForm(forms.Form):
    portal_address = forms.CharField(max_length=255, label="Адрес портала")


class VerificationCodeForm(forms.Form):
    confirmation_code = forms.CharField(max_length=255, label="Код")
