from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Identidade e autenticação (AGENTS.md — Entidades conceituais).

    Sem campos extras por enquanto: perfil profissional e de contratante
    vivem em apps.professionals/apps.clients, ligados a este User (Etapa 1).
    """
