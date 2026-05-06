"""
DRF Serializers for RAG Chatbot API.
"""
import json
from rest_framework import serializers
from .models import Message, TopicCheckpoint, HundredCheckpoint, Persona, ProcessingStatus


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['message_id', 'conversation_id', 'global_index', 'speaker', 'text']


class TopicCheckpointSerializer(serializers.ModelSerializer):
    keywords = serializers.SerializerMethodField()

    class Meta:
        model = TopicCheckpoint
        fields = ['topic_id', 'topic_number', 'start_global_index', 'end_global_index',
                  'conversation_day_start', 'conversation_day_end',
                  'summary', 'keywords', 'created_at']

    def get_keywords(self, obj):
        try:
            return json.loads(obj.keywords)
        except Exception:
            return []


class HundredCheckpointSerializer(serializers.ModelSerializer):
    class Meta:
        model = HundredCheckpoint
        fields = ['checkpoint_id', 'checkpoint_number', 'start_global_index',
                  'end_global_index', 'summary', 'created_at']


class PersonaSerializer(serializers.ModelSerializer):
    data = serializers.SerializerMethodField()

    class Meta:
        model = Persona
        fields = ['persona_id', 'data', 'updated_at']

    def get_data(self, obj):
        return obj.get_data()


class ProcessingStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessingStatus
        fields = ['status', 'current_step', 'progress_pct', 'total_messages',
                  'total_topics', 'total_checkpoints', 'error_message',
                  'started_at', 'finished_at']
