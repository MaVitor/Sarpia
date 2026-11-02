import uuid

from django.conf import settings
from django.db import models


class Presentation(models.Model):
    MODE_CHOICES = [("pdf", "PDF"), ("roteiro", "Roteiro")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="presentations",
    )
    title = models.CharField(max_length=255)
    mode = models.CharField(max_length=10, choices=MODE_CHOICES)
    pages = models.JSONField()
    reference = models.JSONField()
    reference_version = models.CharField(max_length=32)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]


class Attempt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    presentation = models.ForeignKey(
        Presentation,
        on_delete=models.CASCADE,
        related_name="attempts",
    )
    essay = models.TextField()
    feedback = models.JSONField()
    reference_version = models.CharField(max_length=32)
    model_name = models.CharField(max_length=150, blank=True)
    contract_version = models.CharField(max_length=32, blank=True)
    idempotency_key = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["presentation", "idempotency_key"],
                name="unique_attempt_submission",
            )
        ]
