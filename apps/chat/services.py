from datetime import timedelta

from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Block, Message

MAX_MESSAGES_PER_MINUTE = 20


def is_blocked(conversation, sender):
    other = conversation.other_party(sender)
    return Block.objects.filter(blocker=other, blocked=sender).exists()


def send_message(conversation, sender, body):
    body = body.strip()
    if not body:
        raise ValidationError("Mensagem vazia.")
    if is_blocked(conversation, sender):
        raise ValidationError("Você não pode enviar mensagens nesta conversa.")

    recent_count = Message.objects.filter(
        sender=sender, created_at__gte=timezone.now() - timedelta(minutes=1)
    ).count()
    if recent_count >= MAX_MESSAGES_PER_MINUTE:
        raise ValidationError("Limite de mensagens por minuto atingido. Aguarde um instante.")

    return Message.objects.create(conversation=conversation, sender=sender, body=body)


def block_user(conversation, blocker):
    blocked = conversation.other_party(blocker)
    Block.objects.get_or_create(blocker=blocker, blocked=blocked)
