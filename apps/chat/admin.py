from django.contrib import admin

from .models import Block, Conversation, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ["sender", "body", "created_at"]


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ["interest", "created_at"]
    inlines = [MessageInline]


@admin.register(Block)
class BlockAdmin(admin.ModelAdmin):
    list_display = ["blocker", "blocked", "created_at"]
