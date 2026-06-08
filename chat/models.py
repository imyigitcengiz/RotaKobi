from django.conf import settings
from django.db import models


class ChatThread(models.Model):
    KIND_TEAM = 'team'
    KIND_DIRECT = 'direct'
    KIND_CHOICES = [
        (KIND_TEAM, 'Genel'),
        (KIND_DIRECT, 'Özel'),
    ]

    kind = models.CharField(max_length=10, choices=KIND_CHOICES)
    brand = models.ForeignKey(
        'core_settings.BusinessBrand',
        on_delete=models.CASCADE,
        related_name='chat_threads',
        null=True,
        blank=True,
        verbose_name='Marka',
    )
    direct_key = models.CharField(max_length=64, unique=True, null=True, blank=True)
    title = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.title or self.direct_key or f'Thread #{self.pk}'


class ChatMembership(models.Model):
    thread = models.ForeignKey(ChatThread, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_memberships',
    )
    last_read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [('thread', 'user')]

    def __str__(self):
        return f'{self.user_id} @ {self.thread_id}'


class ChatMessage(models.Model):
    thread = models.ForeignKey(ChatThread, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_messages_sent',
    )
    body = models.TextField(max_length=4000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.sender_id}: {self.body[:40]}'
