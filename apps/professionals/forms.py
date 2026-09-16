from django import forms
from django.contrib.gis.geos import Point

from .models import Availability, PortfolioItem, ProfessionalProfile


class ProfessionalProfileForm(forms.ModelForm):
    latitude = forms.DecimalField(required=False, max_digits=9, decimal_places=6, widget=forms.HiddenInput)
    longitude = forms.DecimalField(required=False, max_digits=9, decimal_places=6, widget=forms.HiddenInput)

    class Meta:
        model = ProfessionalProfile
        fields = [
            "main_category",
            "bio",
            "skills",
            "reference_price",
            "location_label",
            "is_available_now",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.location:
            self.fields["latitude"].initial = self.instance.location.y
            self.fields["longitude"].initial = self.instance.location.x

    def save(self, commit=True):
        instance = super().save(commit=False)
        lat = self.cleaned_data.get("latitude")
        lon = self.cleaned_data.get("longitude")
        if lat is not None and lon is not None:
            instance.location = Point(float(lon), float(lat), srid=4326)
        if commit:
            instance.save()
        return instance


class AvailabilityForm(forms.ModelForm):
    class Meta:
        model = Availability
        fields = ["weekday", "start_time", "end_time"]
        widgets = {
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
        }


class PortfolioItemForm(forms.ModelForm):
    class Meta:
        model = PortfolioItem
        fields = ["image", "caption"]
