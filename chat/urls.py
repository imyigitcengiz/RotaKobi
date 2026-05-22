from django.urls import path

from chat import views

urlpatterns = [
    path('api/summary/', views.chat_summary_api, name='chat_summary'),
    path('api/users/', views.chat_users_api, name='chat_users'),
    path('api/threads/<int:thread_id>/messages/', views.chat_messages_api, name='chat_messages'),
    path('api/threads/<int:thread_id>/send/', views.chat_send_api, name='chat_send'),
    path('api/threads/<int:thread_id>/read/', views.chat_read_api, name='chat_read'),
    path('api/direct/', views.chat_direct_api, name='chat_direct'),
    path('api/join-team/', views.chat_join_team_api, name='chat_join_team'),
]
