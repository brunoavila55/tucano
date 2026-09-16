from django import forms
from django.contrib.gis.geos import Point

from .models import Interest, ServiceRequest


class ServiceRequestForm(forms.ModelForm):
    latitude = forms.DecimalField(required=False, max_digits=9, decimal_places=6, widget=forms.HiddenInput)
    longitude = forms.DecimalField(required=False, max_digits=9, decimal_places=6, widget=forms.HiddenInput)

    class Meta:
        model = ServiceRequest
        fields = [
            "category",
            "title",
            "description",
            "positions_count",
            "scheduled_start",
            "location_label",
            "budget",
            "requirements",
            "interest_window",
        ]
        widgets = {
            "scheduled_start": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "description": forms.Textarea(attrs={"rows": 3}),
            "requirements": forms.Textarea(attrs={"rows": 2}),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        lat = self.cleaned_data.get("latitude")
        lon = self.cleaned_data.get("longitude")
        if lat is not None and lon is not None:
            instance.location = Point(float(lon), float(lat), srid=4326)
        if commit:
            instance.save()
        return instance


class InterestForm(forms.ModelForm):
    class Meta:
        model = Interest
        fields = ["message"]
        widgets = {
            "message": forms.TextInput(attrs={"placeholder": "Mensagem curta (opcional)", "maxlength": 280}),
        }


class CancelRequestForm(forms.Form):
    reason = forms.CharField(
        label="Motivo do cancelamento",
        widget=forms.Textarea(attrs={"rows": 2}),
        max_length=255,
    )
