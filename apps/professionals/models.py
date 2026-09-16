from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify

from apps.moderation.validators import validate_file_size

# AGENTS.md — "Foco inicial recomendado": categorias bloqueadas por risco
# jurídico direto a terceiros ou restrição de publicidade (ex.: OAB para
# advocacia), não apenas por terem conselho de classe.
EXCLUDED_CATEGORY_KEYWORDS = [
    "medicina",
    "saúde",
    "saude",
    "advocacia",
    "advogado",
    "segurança privada",
    "seguranca privada",
    "consultoria de investimento",
    "consultor de investimento",
]


class ServiceCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=110, unique=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "service categories"
        ordering = ["name"]

    def clean(self):
        lowered = self.name.lower()
        for keyword in EXCLUDED_CATEGORY_KEYWORDS:
            if keyword in lowered:
                raise ValidationError(
                    f'Categoria bloqueada: "{self.name}" corresponde a uma profissão excluída '
                    "do MVP (AGENTS.md — Foco inicial recomendado)."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ProfessionalProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="professional_profile",
    )
    bio = models.TextField(blank=True)
    main_category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="professionals",
    )
    skills = models.CharField(max_length=300, blank=True, help_text="Separe por vírgula")
    reference_price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    # Ponto exato guardado para calcular distância — nunca exposto na UI
    # (AGENTS.md: "mostrar distância ou região, não a posição exata").
    location = gis_models.PointField(geography=True, srid=4326, null=True, blank=True)
    location_label = models.CharField(
        max_length=150,
        blank=True,
        help_text="Região exibida publicamente (ex.: bairro/cidade) — nunca o endereço exato.",
    )

    is_available_now = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Profissional: {self.user}"


WEEKDAY_CHOICES = [
    (0, "Segunda"),
    (1, "Terça"),
    (2, "Quarta"),
    (3, "Quinta"),
    (4, "Sexta"),
    (5, "Sábado"),
    (6, "Domingo"),
]


class Availability(models.Model):
    professional = models.ForeignKey(
        ProfessionalProfile, on_delete=models.CASCADE, related_name="availabilities"
    )
    weekday = models.PositiveSmallIntegerField(choices=WEEKDAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        ordering = ["weekday", "start_time"]

    def clean(self):
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError("O horário final deve ser depois do horário inicial.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_weekday_display()} {self.start_time}–{self.end_time}"


class PortfolioItem(models.Model):
    professional = models.ForeignKey(
        ProfessionalProfile, on_delete=models.CASCADE, related_name="portfolio_items"
    )
    image = models.ImageField(upload_to="portfolio/", validators=[validate_file_size])
    caption = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.caption or f"Portfólio de {self.professional}"
