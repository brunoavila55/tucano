"""
Django settings for the tucano project.

See docs.djangoproject.com/en/5.2/topics/settings/ for the full reference.
"""

import sys
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, True),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY", default="insecure-dev-key-change-me")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django.contrib.gis",
    # Terceiros
    "channels",
    "allauth",
    "allauth.account",
    # Domínio (stack.md §1)
    "apps.accounts",
    "apps.professionals",
    "apps.clients",
    "apps.requests",
    "apps.chat",
    "apps.reviews",
    "apps.subscriptions",
    "apps.moderation",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Database — PostGIS por padrão (stack.md §4); troque DATABASE_URL para
# sobrescrever (ex.: sqlite só para depuração pontual sem gis).
DATABASES = {
    "default": env.db_url(
        "DATABASE_URL",
        default="postgis://tucano:tucano@db:5432/tucano",
    ),
}

# Redis: broker do Celery (stack.md §5) e camada de canal do Channels (stack.md §3).
REDIS_URL = env("REDIS_URL", default="redis://redis:6379/0")

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [REDIS_URL]},
    },
}

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TIMEZONE = "America/Sao_Paulo"
# Ligado só em teste (via conftest.py) para não depender de worker/broker.
# Roda as tasks Celery em processo durante os testes (sem broker/worker) —
# detectar pytest é mais confiável aqui do que uma env var, porque o
# settings module é importado pelo pytest-django antes de qualquer
# conftest.py rodar.
CELERY_TASK_ALWAYS_EAGER = "pytest" in sys.modules
CELERY_TASK_EAGER_PROPAGATES = CELERY_TASK_ALWAYS_EAGER

# Notificações em camadas (AGENTS.md/stack.md §6) — em branco = canal
# desabilitado, o envio é registrado como "skipped" em vez de falhar.
WEBPUSH_VAPID_PUBLIC_KEY = env("WEBPUSH_VAPID_PUBLIC_KEY", default="")
WEBPUSH_VAPID_PRIVATE_KEY = env("WEBPUSH_VAPID_PRIVATE_KEY", default="")
WEBPUSH_VAPID_ADMIN_EMAIL = env("WEBPUSH_VAPID_ADMIN_EMAIL", default="mailto:admin@example.com")

TWILIO_ACCOUNT_SID = env("TWILIO_ACCOUNT_SID", default="")
TWILIO_AUTH_TOKEN = env("TWILIO_AUTH_TOKEN", default="")
TWILIO_WHATSAPP_FROM = env("TWILIO_WHATSAPP_FROM", default="")

# Expiração automática do chamado (AGENTS.md — "Janela de interesse e
# seleção"): varredura periódica em vez de agendar uma tarefa por chamado,
# para sobreviver a restart do worker/beat sem perder o job.
CELERY_BEAT_SCHEDULE = {
    "expire-due-service-requests": {
        "task": "apps.requests.tasks.expire_due_service_requests",
        "schedule": 30.0,
    },
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

SITE_ID = 1

# django-allauth (stack.md §1) — login por e-mail, sem username separado.
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
LOGIN_REDIRECT_URL = "/perfil/"

if DEBUG:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Internacionalização — produto nacional (Brasil), AGENTS.md decisão #9.
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Mídia em disco local por enquanto (stack.md §8); troca de backend futura
# não deve exigir mudança de código de aplicação.
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
