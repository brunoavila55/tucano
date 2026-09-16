from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class ServiceConfirmation(models.Model):
    """Pergunta separada às duas partes se o serviço ocorreu (AGENTS.md).

    None = ainda não respondeu; True/False = resposta de cada lado.
    """

    interest = models.OneToOneField(
        "requests.Interest", on_delete=models.CASCADE, related_name="confirmation"
    )
    client_confirmed = models.BooleanField(null=True, blank=True)
    professional_confirmed = models.BooleanField(null=True, blank=True)
    client_responded_at = models.DateTimeField(null=True, blank=True)
    professional_responded_at = models.DateTimeField(null=True, blank=True)
    asked_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_legitimate(self):
        """Só libera avaliação quando as duas partes confirmam que ocorreu."""
        return self.client_confirmed is True and self.professional_confirmed is True

    @property
    def has_dispute(self):
        return (
            self.client_confirmed is not None
            and self.professional_confirmed is not None
            and self.client_confirmed != self.professional_confirmed
        )

    def __str__(self):
        return f"Confirmação de {self.interest}"


class Review(models.Model):
    confirmation = models.ForeignKey(ServiceConfirmation, on_delete=models.CASCADE, related_name="reviews")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews_given")
    target = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews_received")
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    contested = models.BooleanField(default=False)
    contest_reason = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["confirmation", "author"], name="unique_review_per_author"),
        ]

    def __str__(self):
        return f"{self.author} → {self.target}: {self.rating}"
