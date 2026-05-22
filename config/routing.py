from django.urls import path

from chat.consumers import TeamChatConsumer
from .consumers import LiveSyncConsumer


websocket_urlpatterns = [
    path("ws/live-sync/", LiveSyncConsumer.as_asgi()),
    path("ws/chat/", TeamChatConsumer.as_asgi()),
]
