from django.contrib import admin

from chat.models import ChatMembership, ChatMessage, ChatThread


class ChatMembershipInline(admin.TabularInline):
    model = ChatMembership
    extra = 0


@admin.register(ChatThread)
class ChatThreadAdmin(admin.ModelAdmin):
    list_display = ('id', 'kind', 'title', 'direct_key', 'updated_at')
    list_filter = ('kind',)
    inlines = [ChatMembershipInline]


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'thread', 'sender', 'created_at', 'body_preview')
    list_filter = ('thread',)

    @admin.display(description='Mesaj')
    def body_preview(self, obj):
        return obj.body[:60]
