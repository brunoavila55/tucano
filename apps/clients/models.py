from django.conf import settings
from django.db import models


class ClientProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="client_profile",
    )
    company_name = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Contratante: {self.user}"


class Favorite(models.Model):
    client = models.ForeignKey(ClientProfile, on_delete=models.CASCADE, related_name="favorites")
    professional = models.ForeignKey(
        "professionals.ProfessionalProfile", on_delete=models.CASCADE, related_name="favorited_by"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["client", "professional"], name="unique_favorite"),
        ]

    def __str__(self):
        return f"{self.client} ❤ {self.professional}"
