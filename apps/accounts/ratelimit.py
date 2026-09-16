from django.core.cache import cache
from django.core.exceptions import PermissionDenied


def enforce_rate_limit(key, limit, window_seconds):
    """Contador de janela fixa no cache compartilhado (Redis) — simples,
    mas suficiente para o MVP sem introduzir mais uma dependência."""
    count = cache.get(key, 0)
    if count >= limit:
        raise PermissionDenied("Limite de tentativas atingido. Tente novamente em alguns minutos.")
    cache.set(key, count + 1, timeout=window_seconds)


class RateLimitMixin:
    """Aplica um limite simples por usuário (ou IP, se anônimo) nas requisições
    POST desta view — autenticação, upload, chat e assinatura (AGENTS.md)."""

    rate_limit_count = 10
    rate_limit_window = 60

    def rate_limit_key(self, request):
        identity = request.user.pk if request.user.is_authenticated else request.META.get("REMOTE_ADDR", "anon")
        return f"ratelimit:{self.__class__.__name__}:{identity}"

    def dispatch(self, request, *args, **kwargs):
        if request.method == "POST":
            enforce_rate_limit(self.rate_limit_key(request), self.rate_limit_count, self.rate_limit_window)
        return super().dispatch(request, *args, **kwargs)
