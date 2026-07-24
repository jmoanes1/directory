"""Chat URL routes."""

from django.urls import path

from chat import views

app_name = "chat"

urlpatterns = [
    path("", views.chat_home, name="home"),
    path("send/", views.chat_send_message, name="send"),
    path("room/<int:room_id>/messages/", views.chat_messages_ajax, name="messages"),
]
