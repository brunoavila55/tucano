from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import DetailView, View

from apps.requests.models import Interest

from . import services
from .models import Conversation


class ConversationDetailView(LoginRequiredMixin, DetailView):
    template_name = "chat/conversation_detail.html"
    context_object_name = "conversation"

    def get_object(self, queryset=None):
        interest = get_object_or_404(Interest, pk=self.kwargs["interest_id"])
        conversation = get_object_or_404(Conversation, interest=interest)
        user = self.request.user
        if user not in (conversation.client_user, conversation.professional_user):
            raise PermissionDenied
        return conversation

    # Limite de histórico carregado de uma vez (AGENTS.md — "implemente
    # paginação e limites... em busca, chat e avaliações").
    MESSAGE_HISTORY_LIMIT = 50

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        recent = list(
            self.object.messages.select_related("sender").order_by("-created_at")[: self.MESSAGE_HISTORY_LIMIT]
        )
        context["chat_messages"] = list(reversed(recent))
        context["other_user"] = self.object.other_party(self.request.user)
        context["is_blocked_by_other"] = services.is_blocked(self.object, self.request.user)
        return context


class BlockUserView(LoginRequiredMixin, View):
    def post(self, request, interest_id):
        interest = get_object_or_404(Interest, pk=interest_id)
        conversation = get_object_or_404(Conversation, interest=interest)
        if request.user not in (conversation.client_user, conversation.professional_user):
            raise PermissionDenied
        services.block_user(conversation, request.user)
        return redirect("chat:detail", interest_id=interest_id)
