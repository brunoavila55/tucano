# AGENTS.md — "Foco inicial recomendado": catálogo aberto, sem lista fechada
# por segmento. Este conjunto inicial cobre os exemplos já validados
# (eventos/gastronomia, casa, projetos pontuais) respeitando as exclusões
# (saúde/medicina clínica, advocacia, segurança privada autônoma,
# consultoria de investimento).
from django.db import migrations
from django.utils.text import slugify

INITIAL_CATEGORIES = [
    "Barista",
    "Bartender",
    "Garçom",
    "Copeiro",
    "Cozinheiro",
    "Recepcionista",
    "Promotor de eventos",
    "DJ",
    "Fotógrafo",
    "Videomaker",
    "Jardinagem",
    "Estética e beleza",
    "Engenharia",
    "Arquitetura",
    "Contabilidade",
    "Manutenção residencial",
    "Aulas particulares",
]


def seed_categories(apps, schema_editor):
    ServiceCategory = apps.get_model("professionals", "ServiceCategory")
    for name in INITIAL_CATEGORIES:
        ServiceCategory.objects.get_or_create(name=name, defaults={"slug": slugify(name)})


def remove_categories(apps, schema_editor):
    ServiceCategory = apps.get_model("professionals", "ServiceCategory")
    ServiceCategory.objects.filter(name__in=INITIAL_CATEGORIES).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("professionals", "0002_servicecategory_professionalprofile_is_available_now_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_categories, remove_categories),
    ]
