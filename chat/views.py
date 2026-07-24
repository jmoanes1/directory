"""Internal company directory chat views."""

import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_POST

from chat.models import ChatMessage, ChatRoom
from employees.ai_search import generate_chat_response


def _get_or_create_assistant_room(user):
    """Get or create the directory assistant chat room for a user."""
    room = ChatRoom.objects.filter(
        room_type=ChatRoom.RoomType.ASSISTANT,
        participants=user,
    ).first()
    if not room:
        room = ChatRoom.objects.create(
            name="Directory Assistant",
            room_type=ChatRoom.RoomType.ASSISTANT,
        )
        room.participants.add(user)
    return room


@login_required
def chat_home(request):
    """Main chat interface with directory assistant and channels."""
    assistant_room = _get_or_create_assistant_room(request.user)
    messages_list = assistant_room.messages.select_related("sender").order_by("created_at")[:50]

    # Direct message rooms
    dm_rooms = ChatRoom.objects.filter(
        room_type=ChatRoom.RoomType.DIRECT,
        participants=request.user,
    ).prefetch_related("participants", "messages")

    return render(request, "chat/home.html", {
        "assistant_room": assistant_room,
        "messages_list": messages_list,
        "dm_rooms": dm_rooms,
    })


@login_required
@require_POST
def chat_send_message(request):
    """Send a message and get AI assistant response."""
    content = request.POST.get("content", "").strip()
    room_id = request.POST.get("room_id")

    if not content:
        return JsonResponse({"error": "Message cannot be empty."}, status=400)

    room = get_object_or_404(ChatRoom, pk=room_id, participants=request.user)

    # Save user message
    user_msg = ChatMessage.objects.create(
        room=room,
        sender=request.user,
        content=content,
        message_type=ChatMessage.MessageType.USER,
    )

    response_data = {"user_message": {
        "id": user_msg.pk,
        "content": user_msg.content,
        "created_at": user_msg.created_at.isoformat(),
    }}

    # Generate AI assistant response for assistant rooms
    if room.room_type == ChatRoom.RoomType.ASSISTANT:
        ai_response = generate_chat_response(content)
        assistant_msg = ChatMessage.objects.create(
            room=room,
            content=ai_response["message"],
            message_type=ChatMessage.MessageType.ASSISTANT,
            metadata={"employees": ai_response.get("employees", []), "type": ai_response.get("type", "text")},
        )
        response_data["assistant_message"] = {
            "id": assistant_msg.pk,
            "content": assistant_msg.content,
            "employees": ai_response.get("employees", []),
            "type": ai_response.get("type", "text"),
            "created_at": assistant_msg.created_at.isoformat(),
        }

    room.save()  # Trigger updated_at
    return JsonResponse(response_data)


@login_required
@require_GET
def chat_messages_ajax(request, room_id):
    """Fetch chat messages for a room."""
    room = get_object_or_404(ChatRoom, pk=room_id, participants=request.user)
    msgs = room.messages.select_related("sender").order_by("created_at")
    return JsonResponse({
        "messages": [
            {
                "id": m.pk,
                "content": m.content,
                "message_type": m.message_type,
                "sender": m.sender.get_full_name() if m.sender else "Assistant",
                "employees": m.metadata.get("employees", []),
                "created_at": m.created_at.isoformat(),
            }
            for m in msgs
        ]
    })
