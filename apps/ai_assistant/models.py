"""
AI Assistant models — conversation history and feedback tracking.
"""
from django.conf import settings
from django.db import models


class Conversation(models.Model):
    """A conversation session between a user and the AI assistant."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_conversations",
        null=True, blank=True,
    )
    session_key = models.CharField(max_length=64, blank=True, default="")
    context_page = models.CharField(
        max_length=255, blank=True, default="",
        help_text="The page/view the user was on when starting the conversation",
    )
    dt_created = models.DateTimeField(auto_now_add=True)
    dt_modified = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-dt_created"]

    def __str__(self):
        return f"Conversation {self.pk} — {self.user or 'anonymous'}"


class Message(models.Model):
    """A single message in a conversation (user question or AI response)."""
    ROLE_CHOICES = [
        ("user", "User"),
        ("assistant", "Assistant"),
        ("system", "System"),
    ]
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    role = models.CharField(max_length=16, choices=ROLE_CHOICES)
    content = models.TextField()
    sources = models.JSONField(
        default=list, blank=True,
        help_text="List of source documents used for RAG context",
    )
    feedback = models.SmallIntegerField(
        null=True, blank=True,
        help_text="User feedback: 1=helpful, -1=not helpful",
    )
    dt_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["dt_created"]

    def __str__(self):
        return f"{self.role}: {self.content[:60]}"
