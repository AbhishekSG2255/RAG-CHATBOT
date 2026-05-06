"""
URL patterns for api app.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('process/', views.ProcessView.as_view(), name='process'),
    path('status/', views.StatusView.as_view(), name='status'),
    path('chat/', views.ChatView.as_view(), name='chat'),
    path('persona/', views.PersonaView.as_view(), name='persona'),
    path('topics/', views.TopicsView.as_view(), name='topics'),
    path('checkpoints/', views.CheckpointsView.as_view(), name='checkpoints'),
    path('stats/', views.StatsView.as_view(), name='stats'),
]
