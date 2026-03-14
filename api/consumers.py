"""
api/consumers.py — WebSocket consumers (Fixed)

Changes:
  - FIX: Replaced all print() with logger.debug / logger.warning.
  - FIX: disconnect() now guards against AttributeError in case connect() 
    failed before setting self.user (was only guarding self.user_group).
"""
import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if self.user.is_authenticated:
            try:
                self.user_group = f"user_{self.user.id}"
                await self.channel_layer.group_add(self.user_group, self.channel_name)
                await self.channel_layer.group_add(f"role_{self.user.role}", self.channel_name)
                await self.channel_layer.group_add("all_users", self.channel_name)
                await self.channel_layer.group_add("online_users", self.channel_name)

                await self.accept()
                logger.debug("WS NotificationConsumer: accepted user %s", self.user.id)

                # Broadcast online status
                await self.channel_layer.group_send(
                    "online_users",
                    {
                        "type": "user_status",
                        "user_id": str(self.user.id),
                        "status": "online"
                    }
                )
            except Exception as e:
                logger.error(
                    "WS NotificationConsumer: connect error for user %s: %s",
                    self.user.id, str(e)
                )
                await self.close()
        else:
            logger.debug("WS NotificationConsumer: rejected — unauthenticated")
            await self.close()

    async def disconnect(self, close_code):
        # FIX: Check for both user_group AND user being set (connect may have
        # failed at different stages)
        if hasattr(self, 'user_group') and hasattr(self, 'user'):
            try:
                await self.channel_layer.group_discard(self.user_group, self.channel_name)
                await self.channel_layer.group_discard(
                    f"role_{self.user.role}", self.channel_name
                )
                await self.channel_layer.group_discard("all_users", self.channel_name)
                await self.channel_layer.group_discard("online_users", self.channel_name)

                # Broadcast offline status
                await self.channel_layer.group_send(
                    "online_users",
                    {
                        "type": "user_status",
                        "user_id": str(self.user.id),
                        "status": "offline"
                    }
                )
                logger.debug("WS NotificationConsumer: disconnected user %s", self.user.id)
            except Exception as e:
                logger.warning("WS NotificationConsumer: disconnect error: %s", str(e))

    async def send_notification(self, event):
        await self.send(text_data=json.dumps({
            "type": "notification",
            "notification": event["notification"]
        }))

    # FIX: Handler name must match the "type" sent by group_send.
    # Signals send type="notification" but this handler was named "send_notification"
    # which would only work if the type was "send.notification".
    async def notification(self, event):
        await self.send(text_data=json.dumps({
            "type": "notification",
            "notification": event["notification"]
        }))

    async def monitoring_update(self, event):
        await self.send(text_data=json.dumps({
            "type": "monitoring_update",
            "monitoring": event["monitoring"]
        }))

    async def user_status(self, event):
        await self.send(text_data=json.dumps({
            "type": "user_status",
            "user_id": event["user_id"],
            "status": event["status"]
        }))


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if self.user.is_authenticated:
            try:
                self.room_group_name = f"chat_{self.user.id}"
                await self.channel_layer.group_add(self.room_group_name, self.channel_name)
                await self.accept()
                logger.debug("WS ChatConsumer: accepted user %s", self.user.id)
            except Exception as e:
                logger.error(
                    "WS ChatConsumer: connect error for user %s: %s",
                    self.user.id, str(e)
                )
                await self.close()
        else:
            logger.debug("WS ChatConsumer: rejected — unauthenticated")
            await self.close()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
            user_id = self.user.id if hasattr(self, 'user') else 'unknown'
            logger.debug("WS ChatConsumer: disconnected user %s", user_id)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            logger.warning("WS ChatConsumer: received invalid JSON from user %s", self.user.id)
            return

        message = data.get("message")
        target_user_id = data.get("target_user_id")

        if target_user_id and message:
            await self.channel_layer.group_send(
                f"chat_{target_user_id}",
                {
                    "type": "chat_message",
                    "message": message,
                    "sender_id": str(self.user.id),
                    "sender_name": self.user.name or self.user.username
                }
            )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            "type": "chat_message",
            "message": event["message"],
            "sender_id": event["sender_id"],
            "sender_name": event["sender_name"]
        }))
