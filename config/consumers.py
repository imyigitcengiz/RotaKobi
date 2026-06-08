from channels.generic.websocket import AsyncJsonWebsocketConsumer

from common.brand_scope import SESSION_ACTIVE_BRAND


class LiveSyncConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            await self.close()
            return

        session = self.scope.get('session')
        brand_id = session.get(SESSION_ACTIVE_BRAND) if session else None
        if not brand_id and not user.is_superuser:
            await self.close()
            return

        if brand_id:
            self.group_name = f'live_updates_brand_{brand_id}'
        else:
            self.group_name = 'live_updates_admin'

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        group_name = getattr(self, 'group_name', None)
        if group_name:
            await self.channel_layer.group_discard(group_name, self.channel_name)

    async def live_event(self, event):
        if event.get('user_id') and self.scope['user'].pk == event.get('user_id'):
            return
        await self.send_json(
            {
                'kind': event.get('kind', 'unknown'),
                'action': event.get('action', 'updated'),
                'id': event.get('id'),
                'message': event.get('message', 'Veriler güncellendi.'),
                'ts': event.get('ts'),
            }
        )
