from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden

from apps.accounts.ratelimit import enforce_rate_limit


class AdminLoginRateLimitMiddleware:
    """O login do Django Admin não passa pelo django-allauth (que já tem
    rate limiting embutido) — protege /admin/login/ separadamente
    (AGENTS.md: "proteja ... painel administrativo")."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == "/admin/login/" and request.method == "POST":
            key = f"ratelimit:admin-login:{request.META.get('REMOTE_ADDR', 'unknown')}"
            try:
                enforce_rate_limit(key, limit=10, window_seconds=300)
            except PermissionDenied:
                return HttpResponseForbidden("Muitas tentativas de login. Tente novamente mais tarde.")
        return self.get_response(request)
