from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied


class RoleRequiredMixin(UserPassesTestMixin):
    """Anônimo -> redireciona para login; autenticado sem o papel certo -> 403."""

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect_to_login(self.request.get_full_path())
        raise PermissionDenied


class ProfessionalRequiredMixin(RoleRequiredMixin):
    def test_func(self):
        return hasattr(self.request.user, "professional_profile")


class ClientRequiredMixin(RoleRequiredMixin):
    def test_func(self):
        return hasattr(self.request.user, "client_profile")
