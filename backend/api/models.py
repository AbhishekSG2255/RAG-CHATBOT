"""
Django models for RAG chatbot system.
"""
from django.db import models
import json


class Message(models.Model):
    """Represents a single message from the CSV dataset."""
    message_id = models.AutoField(primary_key=True)
    conversation_id = models.IntegerField(db_index=True)  # CSV row index (day)
    global_index = models.IntegerField(db_index=True)     # Position across all messages
    speaker = models.CharField(max_length=20)              # 'User 1' or 'User 2'
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['global_index']

    def __str__(self):
        return f"[{self.global_index}] {self.speaker}: {self.text[:60]}"


class TopicCheckpoint(models.Model):
    """A segment of messages that share a topic, with a summary."""
    topic_id = models.AutoField(primary_key=True)
    topic_number = models.IntegerField()
    start_global_index = models.IntegerField()
    end_global_index = models.IntegerField()
    summary = models.TextField()
    keywords = models.TextField()  # JSON list of keywords
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['topic_number']

    def get_keywords(self):
        try:
            return json.loads(self.keywords)
        except Exception:
            return []

    def __str__(self):
        return f"Topic {self.topic_number} (msgs {self.start_global_index}–{self.end_global_index})"


class HundredCheckpoint(models.Model):
    """Every 100 messages, a summary checkpoint."""
    checkpoint_id = models.AutoField(primary_key=True)
    checkpoint_number = models.IntegerField()
    start_global_index = models.IntegerField()
    end_global_index = models.IntegerField()
    summary = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['checkpoint_number']

    def __str__(self):
        return f"100-Checkpoint #{self.checkpoint_number} (msgs {self.start_global_index}–{self.end_global_index})"


class Persona(models.Model):
    """Stores the extracted user persona as JSON."""
    persona_id = models.AutoField(primary_key=True)
    data = models.TextField()  # Full JSON
    updated_at = models.DateTimeField(auto_now=True)

    def get_data(self):
        try:
            return json.loads(self.data)
        except Exception:
            return {}

    def __str__(self):
        return f"Persona (updated {self.updated_at})"


class ProcessingStatus(models.Model):
    """Tracks the state of CSV processing."""
    STATUS_CHOICES = [
        ('idle', 'Idle'),
        ('processing', 'Processing'),
        ('done', 'Done'),
        ('error', 'Error'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='idle')
    current_step = models.CharField(max_length=200, default='')
    progress_pct = models.FloatField(default=0.0)
    total_messages = models.IntegerField(default=0)
    total_topics = models.IntegerField(default=0)
    total_checkpoints = models.IntegerField(default=0)
    error_message = models.TextField(default='')
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Processing Status'

    def __str__(self):
        return f"Status: {self.status} ({self.progress_pct:.1f}%)"
