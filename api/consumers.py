import json
from channels.generic.websocket import AsyncWebsocketConsumer

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if self.user.is_authenticated:
            self.user_group = f"user_{self.user.id}"
            await self.channel_layer.group_add(self.user_group, self.channel_name)
            await self.channel_layer.group_add(f"role_{self.user.role}", self.channel_name)
            await self.channel_layer.group_add("all_users", self.channel_name)
            await self.channel_layer.group_add("online_users", self.channel_name)
            
            await self.accept()
            
            # Notify others about online status
            await self.channel_layer.group_send(
                "online_users",
                {
                    "type": "user_status",
                    "user_id": str(self.user.id),
                    "status": "online"
                }
            )
        else:
            await self.close()

    async def disconnect(self, close_code):
        if hasattr(self, 'user_group'):
            await self.channel_layer.group_discard(self.user_group, self.channel_name)
            await self.channel_layer.group_discard(f"role_{self.user.role}", self.channel_name)
            await self.channel_layer.group_discard("all_users", self.channel_name)
            await self.channel_layer.group_discard("online_users", self.channel_name)
            
            # Notify others about offline status
            await self.channel_layer.group_send(
                "online_users",
                {
                    "type": "user_status",
                    "user_id": str(self.user.id),
                    "status": "offline"
                }
            )

    async def send_notification(self, event):
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
            self.room_group_name = f"chat_{self.user.id}"
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()
        else:
            await self.close()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data.get("message")
        target_user_id = data.get("target_user_id")

        if target_user_id and message:
            # Send to target user's group
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
