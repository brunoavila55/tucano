from django import forms

from .models import NotificationPreference


class NotificationPreferenceForm(forms.ModelForm):
    class Meta:
        model = NotificationPreference
        fields = ["push_enabled", "whatsapp_enabled", "email_enabled"]
