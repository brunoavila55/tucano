from django import forms

from .models import Verification

VERIFICATION_PURPOSE = "Verificação de identidade para exibir selo de verificado no perfil profissional"


class ReportUserForm(forms.Form):
    reason = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), max_length=1000)


class AppealForm(forms.Form):
    reason = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), max_length=1000)


class VerificationRequestForm(forms.ModelForm):
    consent = forms.BooleanField(
        label=f'Autorizo a checagem do meu documento com a finalidade de: "{VERIFICATION_PURPOSE}".',
        required=True,
    )

    class Meta:
        model = Verification
        fields = ["document"]
