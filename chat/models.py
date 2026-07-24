"""Internal company directory chat models."""

from django.conf import settings
from django.db import models


class ChatRoom(models.Model):
    """Chat room for direct messages or group channels."""

    class RoomType(models.TextChoices):
        DIRECT = "direct", "Direct Message"
        CHANNEL = "channel", "Channel"
        ASSISTANT = "assistant", "Directory Assistant"

    name = models.CharField(max_length=100, blank=True)
    room_type = models.CharField(max_length=20, choices=RoomType.choices, default=RoomType.DIRECT)
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="chat_rooms",
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.name or f"Room {self.pk}"

    @property
    def last_message(self):
        return self.messages.order_by("-created_at").first()


class ChatMessage(models.Model):
    """Individual chat message within a room."""

    class MessageType(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"
        SYSTEM = "system", "System"

    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chat_messages",
    )
    content = models.TextField()
    message_type = models.CharField(max_length=20, choices=MessageType.choices, default=MessageType.USER)
    metadata = models.JSONField(default=dict, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        preview = self.content[:50]
        return f"{self.get_message_type_display()}: {preview}"
