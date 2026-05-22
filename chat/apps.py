from django.apps import AppConfig


class ChatConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chat'
    verbose_name = 'Ekip sohbeti'

    def ready(self):
        from django.db.models.signals import post_migrate

        post_migrate.connect(_ensure_team_thread, sender=self)


def _ensure_team_thread(sender, **kwargs):
    if sender.name != 'chat':
        return
    try:
        from chat.services import ensure_team_thread

        ensure_team_thread()
    except Exception:
        pass
